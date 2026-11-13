import type { AxiosRequestConfig } from "axios";
import { httpClient } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";

export const GREEN_GRAM_PREDICTION_ENABLED = process.env.EXPO_PUBLIC_GREEN_GRAM_EXPERIMENTAL_ENABLED === "true";
export const GREEN_GRAM_MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
export const GREEN_GRAM_ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
export type GreenGramClass = "healthy" | "leaf_curl" | "mymv";
export type GreenGramPredictionResponse = { crop: "green_gram"; model_version: string; status: "EXPERIMENTAL_RESULT"; predicted_class: GreenGramClass; confidence: number; top_three_predictions: { class_id: GreenGramClass; confidence: number }[]; supported_classes: GreenGramClass[]; experimental: true; expert_review_required: true; experimental_notice: string };
export type GreenGramUploadImage = { uri: string; mimeType: string; name?: string; fileSize?: number | null };

export function validateGreenGramUpload(image: Pick<GreenGramUploadImage, "mimeType" | "fileSize">) {
  if (!(GREEN_GRAM_ALLOWED_MIME_TYPES as readonly string[]).includes(image.mimeType)) return "unsupported_type" as const;
  if (image.fileSize != null && image.fileSize > GREEN_GRAM_MAX_UPLOAD_BYTES) return "too_large" as const;
  return null;
}
export async function predictGreenGram(image: GreenGramUploadImage): Promise<GreenGramPredictionResponse> {
  if (!GREEN_GRAM_PREDICTION_ENABLED) throw new Error("green_gram_model_not_available");
  const invalid = validateGreenGramUpload(image); if (invalid) throw new Error(invalid);
  const form = new FormData();
  form.append("image", { uri: image.uri, type: image.mimeType, name: image.name ?? `green-gram-${Date.now()}.jpg` } as unknown as Blob);
  const response = await httpClient.post<GreenGramPredictionResponse>(endpoints.disease.greenGramExperimental, form, { _skipRetry: true, timeout: 45_000 } as AxiosRequestConfig);
  return response.data;
}
