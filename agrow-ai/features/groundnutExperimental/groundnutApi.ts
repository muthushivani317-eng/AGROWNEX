import type { AxiosRequestConfig } from "axios";

import { httpClient } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";

import type {
  GroundnutPredictionResponse,
  GroundnutDamageExtent,
  GroundnutPestObservationResponse,
  GroundnutSpreadSpeed,
  GroundnutTextGuidanceResponse,
  GroundnutTextSymptom,
  GroundnutTranscriptMapResponse,
  GroundnutTranscriptResponse,
} from "./types";

export const GROUNDNUT_MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
export const GROUNDNUT_ALLOWED_MIME_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

const noRetry = { _skipRetry: true, timeout: 45_000 } as AxiosRequestConfig;

export type GroundnutUploadImage = {
  uri: string;
  mimeType: string;
  name?: string;
  fileSize?: number | null;
};

export type GroundnutUploadValidationError = "unsupported_type" | "too_large";

export function validateGroundnutUpload(
  image: Pick<GroundnutUploadImage, "mimeType" | "fileSize">,
): GroundnutUploadValidationError | null {
  if (
    !(GROUNDNUT_ALLOWED_MIME_TYPES as readonly string[]).includes(
      image.mimeType,
    )
  ) {
    return "unsupported_type";
  }
  if (image.fileSize != null && image.fileSize > GROUNDNUT_MAX_UPLOAD_BYTES) {
    return "too_large";
  }
  return null;
}

export async function predictGroundnut(
  image: GroundnutUploadImage,
): Promise<GroundnutPredictionResponse> {
  const validationError = validateGroundnutUpload(image);
  if (validationError) throw new Error(validationError);

  const form = new FormData();
  form.append("image", {
    uri: image.uri,
    type: image.mimeType,
    name: image.name ?? `groundnut-${Date.now()}.jpg`,
  } as unknown as Blob);
  const response = await httpClient.post<GroundnutPredictionResponse>(
    endpoints.disease.groundnutExperimental,
    form,
    noRetry,
  );
  return response.data;
}

export async function submitGroundnutPestObservation(
  image: GroundnutUploadImage,
  observation: {
    damageExtent: GroundnutDamageExtent;
    spreadSpeed: GroundnutSpreadSpeed;
    consent: true;
    captureMethod: "camera" | "gallery";
  },
): Promise<GroundnutPestObservationResponse> {
  const validationError = validateGroundnutUpload(image);
  if (validationError) throw new Error(validationError);

  const form = new FormData();
  form.append("image", {
    uri: image.uri,
    type: image.mimeType,
    name: image.name ?? `groundnut-pest-observation-${Date.now()}.jpg`,
  } as unknown as Blob);
  form.append("damage_extent", observation.damageExtent);
  form.append("spread_speed", observation.spreadSpeed);
  form.append("consent", "true");
  form.append("capture_method", observation.captureMethod);
  const response = await httpClient.post<GroundnutPestObservationResponse>(
    endpoints.disease.groundnutPestObservations,
    form,
    noRetry,
  );
  return response.data;
}

export async function getGroundnutTextGuidance(
  symptoms: GroundnutTextSymptom[],
): Promise<GroundnutTextGuidanceResponse> {
  const response = await httpClient.post<GroundnutTextGuidanceResponse>(
    endpoints.disease.groundnutSymptoms,
    { symptoms },
    { _skipRetry: true, timeout: 15_000 } as AxiosRequestConfig,
  );
  return response.data;
}

export type GroundnutSpeechLanguage = "en-IN" | "ta-IN" | "ml-IN";

export async function transcribeGroundnutSymptoms(
  uri: string,
  mimeType: "audio/amr" | "audio/webm",
  language: GroundnutSpeechLanguage,
): Promise<GroundnutTranscriptResponse> {
  const form = new FormData();
  form.append("audio", {
    uri,
    type: mimeType,
    name: mimeType === "audio/webm" ? "groundnut-symptoms.webm" : "groundnut-symptoms.amr",
  } as unknown as Blob);
  form.append("language", language);
  const response = await httpClient.post<GroundnutTranscriptResponse>(
    endpoints.disease.groundnutTranscribe,
    form,
    { _skipRetry: true, timeout: 45_000 } as AxiosRequestConfig,
  );
  return response.data;
}

export async function mapGroundnutTranscript(
  transcript: string,
  language: GroundnutSpeechLanguage,
): Promise<GroundnutTranscriptMapResponse> {
  const response = await httpClient.post<GroundnutTranscriptMapResponse>(
    endpoints.disease.groundnutMapTranscript,
    { transcript, language },
    { _skipRetry: true, timeout: 15_000 } as AxiosRequestConfig,
  );
  return response.data;
}
