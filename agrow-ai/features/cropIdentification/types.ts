export type SupportedCropId = 'banana' | 'paddy' | 'cotton' | 'groundnut' | 'redgram' | 'chilli';
export type CropIdentificationStatus =
  | 'identified' | 'uncertain' | 'unsupported' | 'non_plant'
  | 'invalid_image' | 'service_unavailable';
export interface LocalizedText { en: string; ta: string }
export interface CropIdentificationResult {
  request_id: string;
  status: CropIdentificationStatus;
  identified_crop: SupportedCropId | null;
  display_name: LocalizedText;
  confidence: number | null;
  confidence_source: 'gemini_self_report' | 'heuristic' | 'unavailable';
  farmer_confirmation_required: true;
  reason_code: string;
  reason_message: LocalizedText;
  provider: 'gemini';
  provider_model: string;
  crop_id_version: string;
  quality_checks: { passed: boolean; reason_code: string | null; width: number; height: number; byte_size: number };
  plant_check: { outcome: 'plant' | 'non_plant' | 'uncertain'; method: 'temporary_gemini_provider_assisted' };
  created_at: string;
}
export interface CropConfirmationResult {
  request_id: string;
  confirmed_crop: SupportedCropId;
  crop_source: 'gemini_confirmed' | 'farmer_selected_after_rejection';
  confirmation_token: string;
  confirmed_at: string;
  expires_at: string;
}
