import {
  qualitativeConfidence,
  safeMessageKey,
  visibleClassId,
} from '../responseMapping';
import type { BananaPredictionResponse } from '../types';

function response(status: BananaPredictionResponse['status']): BananaPredictionResponse {
  return {
    request_id: '00000000-0000-4000-8000-000000000001',
    model_version: 'banana-v3.0.0',
    crop: 'banana',
    status,
    decision_code: 'test',
    result: { class_id: 'banana_sigatoka', display_name_key: 'banana.result.sigatoka', confidence: 0.96, margin: 0.5 },
    healthy_gate: { predicted_class: 'diseased', confidence: 0.9, margin: 0.4, accepted: true },
    disease_classifier: { executed: true, predicted_class: 'banana_sigatoka', confidence: 0.96, margin: 0.5, accepted: true },
    message_key: 'banana.result.sigatoka',
    requires_follow_up_photo: status !== 'accepted',
    requires_human_review: status !== 'accepted',
    runtime_backend: 'onnx',
    processing_time_ms: 20,
    timestamp_utc: '2026-07-27T00:00:00Z',
  };
}

test('qualitative confidence never formats a raw percentage', () => {
  expect(qualitativeConfidence(0.96)).toBe('High');
  expect(qualitativeConfidence(0.7)).toBe('Moderate');
  expect(qualitativeConfidence(0.2)).toBe('Low');
  expect(qualitativeConfidence(0.96)).not.toContain('%');
});

test('uncertain response never exposes disease class or disease message', () => {
  const uncertain = response('uncertain');
  expect(visibleClassId(uncertain)).toBeNull();
  expect(safeMessageKey(uncertain)).toBe('banana.result.unable_to_confirm');
  expect(safeMessageKey(uncertain)).not.toContain('sigatoka');
});

test('unknown backend error prose is replaced by safe localized key', () => {
  const failed = { ...response('error'), message_key: 'raw.backend.exception' };
  expect(safeMessageKey(failed)).toBe('banana.error.runtime_failure');
});
