import type { BananaPredictionResponse } from './types';

export type ConfidenceLabel = 'High' | 'Moderate' | 'Low';
export function qualitativeConfidence(confidence: number): ConfidenceLabel {
  return confidence >= 0.85 ? 'High' : confidence >= 0.65 ? 'Moderate' : 'Low';
}
export function safeMessageKey(response: BananaPredictionResponse): string {
  if (response.status === 'uncertain') return 'banana.result.unable_to_confirm';
  if (response.status === 'error') {
    return response.message_key.startsWith('banana.error.')
      ? response.message_key : 'banana.error.runtime_failure';
  }
  return response.message_key;
}
export function visibleClassId(response: BananaPredictionResponse): string | null {
  return response.status === 'accepted' ? response.result.class_id : null;
}
