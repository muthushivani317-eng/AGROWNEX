export type BananaStatus = 'accepted' | 'uncertain' | 'error';
export type BananaRuntime = 'onnx' | 'pytorch';
export type BananaFeedbackChoice =
  | 'CORRECT' | 'INCORRECT' | 'UNSURE' | 'IMAGE_POOR' | 'NOT_BANANA' | 'OTHER';

export interface BananaGate {
  predicted_class: string | null;
  confidence: number;
  margin: number;
  accepted: boolean;
}
export interface BananaPredictionResponse {
  request_id: string;
  model_version: 'banana-v3.0.0';
  crop: 'banana';
  status: BananaStatus;
  decision_code: string;
  result: { class_id: string | null; display_name_key: string | null; confidence: number; margin: number };
  healthy_gate: BananaGate;
  disease_classifier: BananaGate & { executed: boolean };
  message_key: string;
  requires_follow_up_photo: boolean;
  requires_human_review: boolean;
  runtime_backend: BananaRuntime;
  processing_time_ms: number;
  timestamp_utc: string;
}
export interface BananaFeedbackRequest {
  prediction_request_id: string;
  farmer_selected_outcome: BananaFeedbackChoice;
  notes?: string;
  consent: boolean;
  source_context: 'agrowai_mobile_app';
}
