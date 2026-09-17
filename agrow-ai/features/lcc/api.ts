import type { AxiosRequestConfig } from "axios";

import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";

import type { LccResult } from "./types";

export function analyzeLcc(input: {
  farmId: string;
  imageBase64: string;
  mimeType: "image/jpeg" | "image/png" | "image/webp";
}): Promise<LccResult> {
  return api.post<LccResult>(
    endpoints.lcc.analyze,
    {
      farm_id: input.farmId,
      image_base64: input.imageBase64,
      mime_type: input.mimeType,
    },
    { _skipRetry: true, timeout: 30000 } as AxiosRequestConfig,
  );
}
