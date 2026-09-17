export type DatasetVerificationStatus =
  | 'UNREVIEWED'
  | 'EXPERT_REVIEW_PENDING'
  | 'EXPERT_VERIFIED'
  | 'REJECTED';
export type ModelDeploymentStatus =
  | 'NOT_TRAINED'
  | 'TRAINING'
  | 'PROVISIONAL_EVALUATION'
  | 'DEPLOYED_RESEARCH_ONLY'
  | 'PRODUCTION_APPROVED';

export type CropDiagnosisStatus =
  | 'AVAILABLE_FIELD_VALIDATION_IN_PROGRESS'
  | 'LEGACY_JOINT_MODEL_AUDIT_REQUIRED'
  | 'MODEL_PIPELINE_PENDING'
  | 'DATASET_UNRESOLVED'
  | 'MODEL_NOT_COMPLETED'
  | 'RESTRICTED_INTERNAL_TESTING_ONLY'
  | 'NOT_AVAILABLE';

export interface CropCapability {
  crop: string;
  visibleInApp: boolean;
  datasetVerificationStatus: DatasetVerificationStatus;
  diseaseModelStatus: ModelDeploymentStatus;
  diseaseModelAvailable: boolean;
  nutrientModelAvailable: boolean;
  satelliteSupportAvailable: boolean;
  productionApproved: boolean;
  diagnosisStatus: CropDiagnosisStatus;
  modelVersion?: string;
  predictionProvider?: string;
  supportedClassIds: readonly string[];
  apiRoutes?: readonly string[];
  artifactManifestSha256?: string;
  calibrationArtifactSha256?: string;
  thresholdArtifactSha256?: string;
  bundleSha256?: string;
  evidenceReportPath?: string;
  requiresUserCropConfirmation: boolean;
  hasTrainedCropConfirmationGate: boolean;
  fieldValidationStatus: 'IN_PROGRESS' | 'NOT_STARTED';
}

export type CanonicalCropId =
  | 'rice'
  | 'cotton'
  | 'groundnut'
  | 'banana'
  | 'chilli'
  | 'blackgram'
  | 'redgram';

const CROP_ALIASES: Readonly<Record<string, CanonicalCropId>> = {
  rice: 'rice',
  paddy: 'rice',
  paddy_rice: 'rice',
  'paddy (rice)': 'rice',
  'நெல்': 'rice',
  cotton: 'cotton',
  groundnut: 'groundnut',
  banana: 'banana',
  chilli: 'chilli',
  blackgram: 'blackgram',
  redgram: 'redgram',
};

export const CROP_CAPABILITIES: Readonly<Record<string, CropCapability>> = {
  // Runtime availability and authorization are supplied by the authenticated
  // backend capability endpoint. Static metadata must never enable inference.
  banana: capability('banana', 'EXPERT_VERIFIED', 'DEPLOYED_RESEARCH_ONLY', false,
    'AVAILABLE_FIELD_VALIDATION_IN_PROGRESS', {
      modelVersion: 'banana_v3',
      predictionProvider: 'banana_v3_backend',
      apiRoutes: ['/api/v1/disease/banana/predict'],
      evidenceReportPath: 'backend/app/banana_v3/artifacts/manifests/artifact_manifest.json',
      fieldValidationStatus: 'IN_PROGRESS',
    }),
  // The backend registry has these legacy models disabled pending an individual
  // audit.  Do not route farmers to endpoints that are not authorized to
  // diagnose; availability must match that registry.
  rice: capability('rice', 'EXPERT_VERIFIED', 'DEPLOYED_RESEARCH_ONLY', false,
    'LEGACY_JOINT_MODEL_AUDIT_REQUIRED', {
      modelVersion: 'legacy_joint_v1_crop_constrained',
      predictionProvider: 'legacy_joint_backend',
      apiRoutes: ['/api/v1/disease/paddy/predict'],
      supportedClassIds: ['paddy_healthy', 'rice_blast', 'rice_brown_leaf_spot', 'rice_tungro'],
      fieldValidationStatus: 'IN_PROGRESS',
    }),
  cotton: capability('cotton', 'EXPERT_VERIFIED', 'DEPLOYED_RESEARCH_ONLY', false,
    'LEGACY_JOINT_MODEL_AUDIT_REQUIRED', {
      modelVersion: 'legacy_joint_v1_crop_constrained',
      predictionProvider: 'legacy_joint_backend',
      apiRoutes: ['/api/v1/disease/cotton/predict'],
      supportedClassIds: ['cotton_fusarium_wilt', 'cotton_healthy', 'cotton_verticillium_wilt'],
      fieldValidationStatus: 'IN_PROGRESS',
    }),
  groundnut: capability('groundnut', 'EXPERT_VERIFIED', 'DEPLOYED_RESEARCH_ONLY', false,
    'LEGACY_JOINT_MODEL_AUDIT_REQUIRED', {
      modelVersion: 'legacy_joint_v1_crop_constrained',
      predictionProvider: 'legacy_joint_backend',
      apiRoutes: ['/api/v1/disease/groundnut/predict'],
      supportedClassIds: ['groundnut_healthy', 'groundnut_rust'],
      fieldValidationStatus: 'IN_PROGRESS',
    }),
  chilli: capability('chilli', 'EXPERT_VERIFIED', 'DEPLOYED_RESEARCH_ONLY', false,
    'RESTRICTED_INTERNAL_TESTING_ONLY', {
      modelVersion: 'chilli_mobilenetv3_small_v1_restricted',
      predictionProvider: 'restricted_backend',
      apiRoutes: ['/api/v1/disease/chilli/predict-restricted'],
      supportedClassIds: [
        'chilli__bacterial_spot',
        'chilli__cercospora_leaf_spot',
        'chilli__healthy',
        'chilli__leaf_curl_virus',
      ],
      fieldValidationStatus: 'IN_PROGRESS',
    }),
  redgram: capability('redgram', 'EXPERT_VERIFIED', 'DEPLOYED_RESEARCH_ONLY', false,
    'RESTRICTED_INTERNAL_TESTING_ONLY', {
      modelVersion: 'redgram_mobilenetv3_small_v1_restricted',
      predictionProvider: 'restricted_backend',
      apiRoutes: ['/api/v1/disease/redgram/predict-restricted'],
      supportedClassIds: [
        'redgram__healthy',
        'redgram__leaf_spot',
        'redgram__sterility_mosaic',
      ],
      fieldValidationStatus: 'IN_PROGRESS',
    }),
  blackgram: capability('blackgram', 'EXPERT_REVIEW_PENDING', 'NOT_TRAINED', false,
    'DATASET_UNRESOLVED'),
  coconut: capability('coconut', 'EXPERT_REVIEW_PENDING', 'NOT_TRAINED', false,
    'MODEL_NOT_COMPLETED'),
  maize: capability('maize', 'EXPERT_REVIEW_PENDING', 'NOT_TRAINED', false, 'NOT_AVAILABLE'),
  greengram: capability('greengram', 'EXPERT_REVIEW_PENDING', 'NOT_TRAINED', false, 'NOT_AVAILABLE'),
  pearl_millet: capability('pearl_millet', 'EXPERT_REVIEW_PENDING', 'NOT_TRAINED', false, 'NOT_AVAILABLE'),
};

function capability(
  crop: string,
  datasetVerificationStatus: DatasetVerificationStatus,
  diseaseModelStatus: ModelDeploymentStatus,
  diseaseModelAvailable: boolean,
  diagnosisStatus: CropDiagnosisStatus,
  evidence: Partial<CropCapability> = {},
): CropCapability {
  return {
    crop,
    visibleInApp: true,
    datasetVerificationStatus,
    diseaseModelStatus,
    diseaseModelAvailable,
    nutrientModelAvailable: true,
    satelliteSupportAvailable: true,
    productionApproved: false,
    diagnosisStatus,
    supportedClassIds: [],
    requiresUserCropConfirmation: true,
    hasTrainedCropConfirmationGate: false,
    fieldValidationStatus: 'NOT_STARTED',
    ...evidence,
  };
}

export function normalizeCropId(crop: string | null | undefined): string {
  const normalized = crop?.trim().toLocaleLowerCase('en-US') ?? '';
  return CROP_ALIASES[normalized] ?? normalized;
}

export function cropCapability(crop: string): CropCapability | null {
  return CROP_CAPABILITIES[normalizeCropId(crop)] ?? null;
}

export function canUseFrozenDiseaseModel(crop: string): boolean {
  void crop;
  return false;
}
