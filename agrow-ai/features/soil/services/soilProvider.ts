import { buildProfile, isBackendConfigured } from "@/config/env";
import { logger } from "@/lib/logger";

import type {
  Paginated,
  SoilDashboard,
  SoilHistoryEntry,
  SoilRecommendation,
  SoilReport,
  SoilReportInput,
  RemoteSoilOutcome,
} from "../types";

/**
 * Soil Intelligence data source contract. Backed by the AgrowAI soil API + Soil
 * Engine when a backend is configured, otherwise a local offline provider that runs
 * a faithful client-side mirror over MMKV. Future sources (government soil datasets,
 * laboratory APIs, satellite soil layers, Gemini OCR) join behind this seam with no
 * frontend change (docs: provider abstraction). Soil values are never fabricated.
 */
export interface SoilProvider {
  dashboard(
    farmId: string,
    soilTypeHint?: string | null,
  ): Promise<SoilDashboard>;
  latest(farmId: string): Promise<SoilReport>;
  history(
    farmId: string,
    page?: number,
    pageSize?: number,
  ): Promise<Paginated<SoilHistoryEntry>>;
  recommendations(
    farmId: string,
    soilTypeHint?: string | null,
  ): Promise<SoilRecommendation[]>;
  submitReport(input: SoilReportInput): Promise<SoilReport>;
  remoteEstimation(farmId: string): Promise<RemoteSoilOutcome>;
}

export class SoilError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "SoilError";
  }
}

let provider: SoilProvider | null = null;

export function getSoilProvider(): SoilProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiSoilProvider").apiSoilProvider as SoilProvider;
    logger.info("soil", "using api provider");
  } else if (
    buildProfile === "development" ||
    buildProfile === "localStandalone"
  ) {
    provider = require("./localSoilProvider").localSoilProvider as SoilProvider;
    logger.info("soil", "using local provider");
  } else {
    provider = unavailableSoilProvider;
    logger.info("soil", "provider unavailable");
  }
  return provider;
}

const unavailable = async (): Promise<never> => {
  throw new SoilError(
    "remote_estimation_unavailable",
    "Soil Intelligence is unavailable. No sample soil result was generated.",
  );
};

export const unavailableSoilProvider: SoilProvider = {
  dashboard: unavailable,
  latest: unavailable,
  async history() {
    return { items: [], page: 1, pageSize: 0, total: 0, totalPages: 0 };
  },
  async recommendations() {
    return [];
  },
  submitReport: unavailable,
  remoteEstimation: unavailable,
};

/** Test seam: force a provider (used to reset between tests). */
export function _setSoilProvider(next: SoilProvider | null): void {
  provider = next;
}
