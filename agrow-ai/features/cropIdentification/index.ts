// The legacy four-class API (cropIdentificationApi.ts) was removed (2026-08
// pre-release audit: confirmed dead -- DiseaseScreen has used only the
// six-class internal API below for some time, and nothing else imported it).
export { confirmInternalCrop, identifyCropInternalOnly } from './internalSixClassApi';
export type { InternalConfirmationResult, InternalSixClassResult } from './internalSixClassApi';
export { internalSafetyMessages, messageForInternalReason } from './internalSafetyMessages';
export type {
  CropIdentificationResult,
  CropIdentificationStatus,
  SupportedCropId,
  CropConfirmationResult,
} from './types';
