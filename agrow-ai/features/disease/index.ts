export { DiseaseScreen } from './screens/DiseaseScreen';
export { GeneralDiagnosisScreen } from './screens/GeneralDiagnosisScreen';
export { DiseaseDetailScreen } from './screens/DiseaseDetailScreen';
export { DiseaseHistoryScreen } from './screens/DiseaseHistoryScreen';
export { useDiseaseHistory } from './hooks/useDisease';
export type { DiseaseReport, DiseaseReportSummary } from './types';

// Reusable photo-capture utilities (shared with the Crop Growth Monitor so the
// camera/gallery picker and client-side quality gate are not duplicated).
export { captureFromCamera, pickFromGallery } from './utils/pickDiseaseImage';
export { checkImageQuality } from './utils/imageQuality';
export { QUALITY_ISSUE_KEY } from './constants';
export type { PickedImage, CaptureMethod } from './types';
