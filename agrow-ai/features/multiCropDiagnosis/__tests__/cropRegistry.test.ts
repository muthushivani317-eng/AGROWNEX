import {
  OFFLINE_UNAVAILABLE,
  assertSafeCrop,
  fetchCropAvailability,
  fetchDiseaseCapabilities,
  maySubmitDiagnosis,
  toMobileCropRegistryEntry,
  resolveDiseaseCapability,
  parseDiseaseCapabilities,
  type PublicCropAvailability,
} from '../cropRegistry';
import type { BuildProfile } from '@/config/env';
import { api } from '@/services/apiClient';

jest.mock('@/services/apiClient', () => ({
  api: { get: jest.fn() },
}));

const crop = (overrides: Partial<PublicCropAvailability> = {}): PublicCropAvailability => ({
  crop_id: 'banana',
  display_name_en: 'Banana',
  display_name_ta: 'Crop availability unavailable',
  model_status: 'FROZEN_RUNTIME_READY',
  crop_enabled: true,
  disease_detection_enabled: true,
  advisory_enabled: false,
  limitation_message_en: 'Provisional.',
  limitation_message_ta: 'Crop model availability could not be verified offline.',
  official_accuracy_claim: false,
  field_validation_status: 'IN_PROGRESS',
  technical_runtime_ready: true,
  internal_testing_eligible: true,
  pilot_testing_eligible: false,
  general_farmer_inference_authorized: false,
  api_integrated: true,
  ...overrides,
});

describe('server-authoritative disease capability policy', () => {
  const raw = {
    crop_id: 'paddy',
    visible: true,
    runtime_ready: true,
    integrity_verified: true,
    adapter_available: true,
    release_scope: 'internal',
    user_authorized: true,
    field_validation_status: 'IN_PROGRESS',
    supported_class_ids: ['paddy_healthy', 'rice_blast'],
    prediction_kind: 'legacy_joint',
  } as const;

  it.each([
    ['internal_testing', true],
    ['kvk_field_test', true],
    ['pilot', false],
    ['production', false],
    ['development', false],
  ] as const)('applies the %s build boundary', (profile, selectable) => {
    expect(resolveDiseaseCapability(raw, profile as BuildProfile).selectable).toBe(selectable);
  });

  it('requires server authorization even in an internal build', () => {
    expect(resolveDiseaseCapability({ ...raw, user_authorized: false }, 'internal_testing'))
      .toMatchObject({ selectable: false, disabledReason: 'TESTER_ROLE_REQUIRED' });
  });

  it('fails closed when security fields are absent or malformed', () => {
    const parsed = parseDiseaseCapabilities({ crops: [{ crop_id: 'banana', runtime_ready: true }] });
    expect(parsed.crops[0]).toMatchObject({ cropId: 'banana', selectable: false });
    expect(parsed.cropIdentification.selectable).toBe(false);
  });

  it('accepts backend field aliases without accepting arbitrary route URLs', () => {
    const parsed = parseDiseaseCapabilities({
      crop_identification: {
        runtime_ready: true, integrity_verified: true, adapter_available: true,
        user_authorized: true, release_scope: 'pilot',
      },
      crops: [{
        crop_id: 'rice', technical_runtime_ready: true, local_integrity_verified: true,
        api_integrated: true, user_authorized: true, release_scope: 'pilot',
        prediction_provider: 'legacy_joint_backend', supported_class_ids: ['rice_blast'],
        api_routes: ['https://attacker.invalid/predict'],
      }],
    }, 'pilot');
    expect(parsed.cropIdentification.selectable).toBe(true);
    expect(parsed.crops[0]).toMatchObject({ cropId: 'rice', selectable: true, predictionKind: 'legacy_joint' });
    expect(parsed.crops[0]).not.toHaveProperty('apiRoutes');
  });

  it.each(['CONTROLLED_TESTING_ONLY', 'RESTRICTED_INTERNAL_TESTING_ONLY'])(
    'treats transitional scope %s as internal and accepts supported_classes',
    (release_scope) => {
      const result = resolveDiseaseCapability({
        ...raw,
        release_scope,
        supported_class_ids: undefined,
        supported_classes: ['rice_blast'],
      }, 'internal_testing');
      expect(result).toMatchObject({ selectable: true, supportedClassIds: ['rice_blast'] });
    },
  );
});

describe('model-independent crop registry', () => {
  it('allows submission only for enabled frozen runtimes', () => {
    expect(maySubmitDiagnosis(crop())).toBe(true);
    expect(maySubmitDiagnosis(crop({
      crop_id: 'coconut',
      model_status: 'MODEL_NOT_COMPLETED',
      disease_detection_enabled: false,
    }))).toBe(false);
  });

  it('rejects an unavailable crop accidentally enabled for diagnosis', () => {
    expect(() => assertSafeCrop(crop({
      model_status: 'DATASET_UNRESOLVED',
      disease_detection_enabled: true,
    }))).toThrow('UNAVAILABLE_CROP_ENABLED');
  });

  it('fails closed when the registry is offline', async () => {
    jest.mocked(api.get).mockRejectedValueOnce(new Error('offline'));
    expect(await fetchCropAvailability()).toEqual([OFFLINE_UNAVAILABLE]);
  });

  it('loads the authenticated workflow contract through the unwrapped API helper', async () => {
    jest.mocked(api.get).mockResolvedValueOnce({
      crop_identification: {
        runtime_ready: true, integrity_verified: true, adapter_available: true,
        user_authorized: true, release_scope: 'internal',
      },
      crops: [],
    });
    const result = await fetchDiseaseCapabilities('internal_testing');
    expect(api.get).toHaveBeenCalledWith('/disease/capabilities');
    expect(result.cropIdentification.selectable).toBe(true);
  });

  it('keeps the separate unvalidated Redgram V2 candidate disabled for farmers', () => {
    const redgram = crop({
      crop_id: 'redgram',
      display_name_en: 'Redgram',
      model_status: 'FROZEN_RUNTIME_READY',
      disease_detection_enabled: false,
      field_validation_status: 'SEALED_TEST_UNOPENED_NOT_DEPLOYED',
      limitation_message_en:
        'This Redgram V2 candidate is not deployed and its sealed test has never been opened. The active restricted runtime is redgram_mobilenetv3_small_v1_restricted.',
    });
    expect(assertSafeCrop(redgram)).toBe(redgram);
    expect(maySubmitDiagnosis(redgram)).toBe(false);
    expect(redgram.official_accuracy_claim).toBe(false);
    expect(redgram).not.toHaveProperty('runtime_path');
    expect(redgram).not.toHaveProperty('checkpoint_sha256');
    expect(redgram).not.toHaveProperty('architecture');
  });

  it('derives internal readiness from backend evidence', () => {
    expect(toMobileCropRegistryEntry(crop(), true)).toMatchObject({
      cropId: 'banana',
      backendCropId: 'banana',
      selectable: true,
      readiness: 'internal_test_ready',
      generalFarmerInferenceAuthorized: false,
    });
  });

  it.each([
    ['chilli', 'MODEL_PIPELINE_PENDING'],
    ['redgram', 'FROZEN_RUNTIME_READY'],
  ] as const)('keeps %s disabled when backend does not authorize testing', (cropId, modelStatus) => {
    const entry = toMobileCropRegistryEntry(crop({
      crop_id: cropId,
      model_status: modelStatus,
      disease_detection_enabled: false,
      technical_runtime_ready: cropId === 'redgram',
      internal_testing_eligible: false,
    }), cropId === 'redgram');
    expect(entry.selectable).toBe(false);
    expect(entry.generalFarmerInferenceAuthorized).toBe(false);
  });

  it('fails closed when an adapter is missing despite a ready runtime', () => {
    expect(toMobileCropRegistryEntry(crop(), false).readiness).toBe('adapter_missing');
  });
});
