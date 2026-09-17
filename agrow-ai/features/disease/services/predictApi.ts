import type { AxiosRequestConfig } from 'axios';

import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

import type { ApiDiseaseReport, DiseaseReport } from '../types';
import { apiToReport } from './diseaseMapper';

// The vision-model read (OpenAI) can legitimately take 15-30s under load —
// well past the client's default 20s timeout (2026-09-03: two genuine farmer
// requests succeeded at 15s/19s, another was aborted client-side at 20s and
// misreported as "no network" even though it reached the server). Give this
// call more room before the client gives up, and never auto-retry it —
// retrying an already-slow call only compounds the wait and risks tripping
// the per-farmer rate limit (also observed same day: 10 straight 429s after
// repeated manual retries).
const PREDICT_TIMEOUT_MS = 45000;
const noRetry = {
  _skipRetry: true,
  timeout: PREDICT_TIMEOUT_MS,
} as AxiosRequestConfig;

type UploadImage = { uri: string; mimeType: string; name?: string };

/**
 * General-release diagnosis (docs/AI_DECISION_MATRIX.md → DISEASE DETECTION,
 * docs/API_CONTRACT.md → DISEASE DETECTION; endpoint POST /disease/predict).
 * Open to any authenticated farmer for any crop — unlike the
 * controlled-tester flows (banana_v3 / restricted / legacy joint), this
 * always returns a farmer-facing answer. It is backed by an OpenAI vision
 * read, cross-checked against a trained local classifier where one exists
 * for the crop. The response's `verificationLevel` tells the UI which case
 * applies for THIS report — `'verified_by_local_model'` when a purpose-
 * trained classifier independently agreed, `'ai_vision_estimate'` otherwise
 * (no local model for this crop, or it disagreed) — and every screen that
 * renders this result must surface that distinction rather than presenting
 * both with equal confidence. See farmer_diagnosis_service.py's module
 * docstring for the full rationale (today's local models are provisional,
 * public-dataset models not yet validated on real farmer photos).
 */
export async function predictDiseaseGeneral(
  crop: string,
  image: UploadImage,
  farmId?: string,
): Promise<DiseaseReport> {
  const form = new FormData();
  form.append('image', {
    uri: image.uri,
    type: image.mimeType,
    name: image.name ?? `${crop}-${Date.now()}.jpg`,
  } as unknown as Blob);
  form.append('crop', crop);
  if (farmId) form.append('farm_id', farmId);
  const data = await api.post<ApiDiseaseReport>(
    endpoints.disease.predict,
    form,
    { ...noRetry },
  );
  return apiToReport(data);
}
