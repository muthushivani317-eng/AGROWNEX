import { api } from '@/services/apiClient';
import { buildProfile, type BuildProfile } from '@/config/env';
import { normalizeCropId } from '@/config/cropCapabilities';

export type CapabilityReleaseScope = 'internal' | 'pilot' | 'general' | 'blocked';
export type DiseasePredictionKind = 'banana_v3' | 'legacy_joint' | 'restricted';

export interface ResolvedDiseaseCapability {
  cropId: string;
  visible: boolean;
  selectable: boolean;
  runtimeReady: boolean;
  integrityVerified: boolean;
  adapterAvailable: boolean;
  userAuthorized: boolean;
  releaseScope: CapabilityReleaseScope;
  fieldValidationStatus: string;
  supportedClassIds: readonly string[];
  predictionKind: DiseasePredictionKind | null;
  disabledReason?: string;
}

export interface DiseaseCapabilitySnapshot {
  crops: ResolvedDiseaseCapability[];
  cropIdentification: ResolvedDiseaseCapability;
}

export type ModelAvailabilityStatus =
  | 'FROZEN_RUNTIME_READY'
  | 'MODEL_PIPELINE_PENDING'
  | 'MODEL_NOT_COMPLETED'
  | 'DATASET_UNRESOLVED'
  | 'LEGACY_JOINT_MODEL_AUDIT_REQUIRED'
  | 'DISABLED';

export type MobileCropReadiness =
  | 'internal_test_ready'
  | 'pilot_test_ready'
  | 'general_farmer_ready'
  | 'testing_blocked'
  | 'runtime_missing'
  | 'adapter_missing'
  | 'disabled';

export interface PublicCropAvailability {
  crop_id: string;
  display_name_en: string;
  display_name_ta: string;
  model_status: ModelAvailabilityStatus;
  crop_enabled: boolean;
  disease_detection_enabled: boolean;
  advisory_enabled: boolean;
  limitation_message_en: string;
  limitation_message_ta: string;
  official_accuracy_claim: false;
  field_validation_status: string;
  technical_runtime_ready?: boolean;
  internal_testing_eligible?: boolean;
  pilot_testing_eligible?: boolean;
  general_farmer_inference_authorized?: boolean;
  api_integrated?: boolean;
}

export interface DiseaseCropRegistryEntry {
  cropId: string;
  displayName: string;
  backendCropId: string;
  visible: boolean;
  selectable: boolean;
  readiness: MobileCropReadiness;
  generalFarmerInferenceAuthorized: boolean;
  fieldValidationComplete: boolean;
  disabledReason?: string;
}

export const OFFLINE_UNAVAILABLE: PublicCropAvailability = {
  crop_id: 'unknown',
  display_name_en: 'Crop availability unavailable',
  display_name_ta: 'Crop availability unavailable',
  model_status: 'DISABLED',
  crop_enabled: false,
  disease_detection_enabled: false,
  advisory_enabled: false,
  limitation_message_en: 'Crop model availability could not be verified offline.',
  limitation_message_ta: 'Crop model availability could not be verified offline.',
  official_accuracy_claim: false,
  field_validation_status: 'NOT_VERIFIED',
};

export async function fetchCropAvailability(): Promise<PublicCropAvailability[]> {
  try {
    const crops = await api.get<PublicCropAvailability[]>('/crops');
    return crops.map(assertSafeCrop);
  } catch {
    return [OFFLINE_UNAVAILABLE];
  }
}

function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function bool(value: unknown): boolean {
  return value === true;
}

function releaseScope(value: unknown): CapabilityReleaseScope {
  const normalized = typeof value === 'string' ? value.toLowerCase() : '';
  if (normalized === 'internal' || normalized === 'internal_testing'
      || normalized === 'controlled_testing_only'
      || normalized === 'restricted_internal_testing_only') return 'internal';
  if (normalized === 'pilot' || normalized === 'pilot_testing') return 'pilot';
  if (normalized === 'general' || normalized === 'production') return 'general';
  return 'blocked';
}

function predictionKind(value: Record<string, unknown>): DiseasePredictionKind | null {
  const candidate = String(value.prediction_kind ?? value.prediction_provider ?? '').toLowerCase();
  if (candidate.includes('banana')) return 'banana_v3';
  if (candidate.includes('legacy') || candidate.includes('joint')) return 'legacy_joint';
  if (candidate.includes('restricted')) return 'restricted';
  return null;
}

function buildAllows(scope: CapabilityReleaseScope, profile: BuildProfile): boolean {
  if (scope === 'general') return profile === 'production' || profile === 'pilot'
    || profile === 'internal_testing' || profile === 'kvk_field_test';
  if (scope === 'pilot') return profile === 'pilot' || profile === 'internal_testing'
    || profile === 'kvk_field_test';
  if (scope === 'internal') return profile === 'internal_testing' || profile === 'kvk_field_test';
  return false;
}

export function resolveDiseaseCapability(
  rawValue: unknown,
  profile: BuildProfile = buildProfile,
  workflow = false,
): ResolvedDiseaseCapability {
  const raw = object(rawValue);
  const cropId = normalizeCropId(typeof raw.crop_id === 'string' ? raw.crop_id : 'unknown');
  const runtimeReady = bool(raw.runtime_ready ?? raw.technical_runtime_ready ?? raw.local_runtime_ready);
  const integrityVerified = bool(raw.integrity_verified ?? raw.local_integrity_verified);
  const adapterAvailable = bool(raw.adapter_available ?? raw.api_integrated);
  const userAuthorized = bool(raw.user_authorized ?? raw.inference_authorized_for_user);
  const scope = releaseScope(raw.release_scope ?? raw.authorized_release_scope);
  const kind = workflow ? null : predictionKind(raw);
  const rawSupportedClasses = raw.supported_class_ids ?? raw.supported_classes;
  const supportedClassIds = Array.isArray(rawSupportedClasses)
    ? rawSupportedClasses.filter((item): item is string => typeof item === 'string')
    : [];
  const selectable = runtimeReady && integrityVerified && adapterAvailable && userAuthorized
    && buildAllows(scope, profile) && (workflow || kind !== null);
  let disabledReason = typeof raw.reason_unavailable === 'string'
    ? raw.reason_unavailable
    : typeof raw.disabled_reason === 'string' ? raw.disabled_reason : undefined;
  if (!disabledReason && !userAuthorized) disabledReason = 'TESTER_ROLE_REQUIRED';
  else if (!disabledReason && !runtimeReady) disabledReason = 'RUNTIME_NOT_READY';
  else if (!disabledReason && !integrityVerified) disabledReason = 'MODEL_INTEGRITY_FAILURE';
  else if (!disabledReason && !adapterAvailable) disabledReason = 'ADAPTER_NOT_AVAILABLE';
  else if (!disabledReason && !buildAllows(scope, profile)) disabledReason = 'RELEASE_NOT_AUTHORIZED';
  else if (!disabledReason && !workflow && kind === null) disabledReason = 'ADAPTER_NOT_AVAILABLE';
  return {
    cropId,
    visible: raw.visible !== false,
    selectable,
    runtimeReady,
    integrityVerified,
    adapterAvailable,
    userAuthorized,
    releaseScope: scope,
    fieldValidationStatus: typeof raw.field_validation_status === 'string'
      ? raw.field_validation_status : 'NOT_VERIFIED',
    supportedClassIds,
    predictionKind: kind,
    ...(disabledReason ? { disabledReason } : {}),
  };
}

const BLOCKED_WORKFLOW = resolveDiseaseCapability({
  crop_id: 'crop_identification', release_scope: 'blocked', reason_unavailable: 'CAPABILITY_UNAVAILABLE',
}, buildProfile, true);

export function parseDiseaseCapabilities(
  value: unknown,
  profile: BuildProfile = buildProfile,
): DiseaseCapabilitySnapshot {
  const body = object(value);
  const rawCrops = Array.isArray(value) ? value : Array.isArray(body.crops) ? body.crops : [];
  const cropIdentificationRaw = body.crop_identification ?? body.crop_identity;
  return {
    crops: rawCrops.map((crop) => resolveDiseaseCapability(crop, profile)),
    cropIdentification: cropIdentificationRaw
      ? resolveDiseaseCapability(cropIdentificationRaw, profile, true)
      : { ...BLOCKED_WORKFLOW },
  };
}

export async function fetchDiseaseCapabilities(
  profile: BuildProfile = buildProfile,
): Promise<DiseaseCapabilitySnapshot> {
  const value = await api.get<unknown>('/disease/capabilities');
  return parseDiseaseCapabilities(value, profile);
}

export function findDiseaseCapability(
  snapshot: DiseaseCapabilitySnapshot | undefined,
  crop: string,
): ResolvedDiseaseCapability | null {
  const cropId = normalizeCropId(crop);
  return snapshot?.crops.find((item) => item.cropId === cropId) ?? null;
}

export function assertSafeCrop(crop: PublicCropAvailability): PublicCropAvailability {
  if (crop.official_accuracy_claim !== false) throw new Error('INVALID_ACCURACY_CLAIM');
  if (crop.model_status !== 'FROZEN_RUNTIME_READY' && crop.disease_detection_enabled) {
    throw new Error('UNAVAILABLE_CROP_ENABLED');
  }
  return crop;
}

export function maySubmitDiagnosis(crop: PublicCropAvailability): boolean {
  return crop.crop_enabled
    && crop.model_status === 'FROZEN_RUNTIME_READY'
    && crop.disease_detection_enabled
    && crop.technical_runtime_ready === true
    && crop.internal_testing_eligible === true;
}

export function toMobileCropRegistryEntry(
  crop: PublicCropAvailability,
  adapterAvailable: boolean,
): DiseaseCropRegistryEntry {
  assertSafeCrop(crop);
  const fieldValidationComplete = crop.field_validation_status === 'COMPLETE';
  const generalFarmerInferenceAuthorized =
    crop.general_farmer_inference_authorized === true && fieldValidationComplete;

  let readiness: MobileCropReadiness = 'testing_blocked';
  let disabledReason: string | undefined = crop.limitation_message_en;
  if (!crop.crop_enabled) readiness = 'disabled';
  else if (crop.technical_runtime_ready !== true) readiness = 'runtime_missing';
  else if (!adapterAvailable || crop.api_integrated !== true) readiness = 'adapter_missing';
  else if (generalFarmerInferenceAuthorized) {
    readiness = 'general_farmer_ready';
    disabledReason = undefined;
  } else if (crop.pilot_testing_eligible === true) {
    readiness = 'pilot_test_ready';
    disabledReason = 'Pilot testing only; general farmer inference is not authorized.';
  } else if (crop.internal_testing_eligible === true) {
    readiness = 'internal_test_ready';
    disabledReason = 'Ready for controlled internal testing; field validation is pending.';
  }

  return {
    cropId: crop.crop_id,
    displayName: crop.display_name_en,
    backendCropId: crop.crop_id,
    visible: true,
    selectable:
      readiness === 'internal_test_ready'
      || readiness === 'pilot_test_ready'
      || readiness === 'general_farmer_ready',
    readiness,
    generalFarmerInferenceAuthorized,
    fieldValidationComplete,
    ...(disabledReason ? { disabledReason } : {}),
  };
}
