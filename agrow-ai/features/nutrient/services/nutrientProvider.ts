import { buildProfile, isBackendConfigured } from "@/config/env";
import { logger } from "@/lib/logger";

import type {
  AnalyzeInput,
  NutrientRecommendation,
  NutrientReport,
} from "../types";

/**
 * Nutrient Deficiency data source contract. Backed by the AgrowAI nutrient API
 * (Gemini vision + the corroboration engine + R2) when a backend is configured,
 * otherwise a local offline provider that runs a faithful client mirror of the
 * engine over MMKV. Designed so a future CV model (YOLO / EfficientNet / ConvNeXt /
 * ONNX / ensemble) can replace Gemini with no frontend change. A deficiency is
 * never fabricated — an inconclusive analysis is honestly "not confirmed".
 */
export interface NutrientProvider {
  analyze(input: AnalyzeInput): Promise<NutrientReport>;
  history(farmId: string): Promise<NutrientReport[]>;
  latest(farmId: string): Promise<NutrientReport | null>;
  recommendations(farmId: string): Promise<NutrientRecommendation[]>;
  getReport(id: string): Promise<NutrientReport>;
}

export class NutrientError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "NutrientError";
  }
}

let provider: NutrientProvider | null = null;

export function getNutrientProvider(): NutrientProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiNutrientProvider")
      .apiNutrientProvider as NutrientProvider;
    logger.info("nutrient", "using api provider");
  } else if (
    buildProfile === "development" ||
    buildProfile === "localStandalone"
  ) {
    provider = require("./localNutrientProvider")
      .localNutrientProvider as NutrientProvider;
    logger.info("nutrient", "using local provider");
  } else {
    provider = unavailableNutrientProvider;
    logger.info("nutrient", "provider unavailable");
  }
  return provider;
}

const unavailable = async (): Promise<never> => {
  throw new NutrientError(
    "analysis_unavailable",
    "Nutrient analysis is unavailable. No sample result was generated.",
  );
};

export const unavailableNutrientProvider: NutrientProvider = {
  analyze: unavailable,
  async history() {
    return [];
  },
  async latest() {
    return null;
  },
  async recommendations() {
    return [];
  },
  getReport: unavailable,
};

/** Test seam: force a provider (used to reset between tests). */
export function _setNutrientProvider(next: NutrientProvider | null): void {
  provider = next;
}
