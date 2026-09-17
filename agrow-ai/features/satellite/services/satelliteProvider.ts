import { buildProfile, isBackendConfigured } from "@/config/env";
import { logger } from "@/lib/logger";

import type {
  Paginated,
  SatelliteAlert,
  SatelliteDashboard,
  SatelliteHistoryEntry,
  SatelliteSession,
  SatelliteTimeline,
} from "../types";

/**
 * Satellite Intelligence data source contract. Backed by the AgrowAI satellite API
 * + Sentinel-2 engine when a backend is configured, otherwise a local offline
 * provider that runs a faithful client mirror over MMKV (deterministic *sample*
 * data, clearly flagged). Future sources (Sentinel Hub, Copernicus, Planet, Maxar,
 * Earth Engine, drone/thermal/hyperspectral) join behind this seam with no frontend
 * change. Imagery and indices are never fabricated as if real.
 */
export interface SatelliteProvider {
  dashboard(farmId: string, hasPolygon?: boolean): Promise<SatelliteDashboard>;
  history(
    farmId: string,
    page?: number,
    pageSize?: number,
  ): Promise<Paginated<SatelliteHistoryEntry>>;
  timeline(farmId: string, range: string): Promise<SatelliteTimeline>;
  alerts(farmId: string): Promise<SatelliteAlert[]>;
  refresh(farmId: string, hasPolygon?: boolean): Promise<SatelliteSession>;
}

export class SatelliteError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "SatelliteError";
  }
}

let provider: SatelliteProvider | null = null;

const unavailable = (farmId: string): SatelliteSession => ({
  id: `unavailable-${farmId}`,
  farmId,
  provider: "copernicus",
  status: "unavailable",
  unavailableReason: "provider_not_configured",
  isSample: false,
  captureDate: null,
  cloudCover: null,
  resolutionM: null,
  ndvi: null,
  ndre: null,
  evi: null,
  ndmi: null,
  vegetationHealth: null,
  stressLevel: null,
  moistureStatus: null,
  trend: null,
  ndviDelta: null,
  confidence: 0,
  metadata: null,
  createdAt: new Date(0).toISOString(),
  images: [],
  indices: [],
  alerts: [],
});

export const unavailableSatelliteProvider: SatelliteProvider = {
  async dashboard(farmId, hasPolygon = true) {
    const session = unavailable(farmId);
    return {
      farmId,
      hasPolygon,
      hasData: false,
      status: "unavailable",
      unavailableReason: hasPolygon ? "provider_not_configured" : "no_polygon",
      messageCode: hasPolygon
        ? "satellite.status.provider_not_configured"
        : "satellite.status.no_polygon",
      session,
      alerts: [],
      dataSource: "live",
    };
  },
  async history() {
    return { items: [], page: 1, pageSize: 0, total: 0, totalPages: 1 };
  },
  async timeline(farmId, range) {
    return { farmId, range, points: [] };
  },
  async alerts() {
    return [];
  },
  async refresh(farmId) {
    return unavailable(farmId);
  },
};

export function getSatelliteProvider(): SatelliteProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiSatelliteProvider")
      .apiSatelliteProvider as SatelliteProvider;
    logger.info("satellite", "using api provider");
    logger.info("satellite", "provider_configured", {
      provider_configured: true,
    });
  } else if (
    buildProfile === "development" ||
    buildProfile === "localStandalone"
  ) {
    provider = require("./localSatelliteProvider")
      .localSatelliteProvider as SatelliteProvider;
    logger.info("satellite", "using local provider");
    logger.info("satellite", "provider_configured", {
      provider_configured: false,
    });
  } else {
    provider = unavailableSatelliteProvider;
    logger.info("satellite", "provider unavailable", {
      provider_configured: false,
    });
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setSatelliteProvider(next: SatelliteProvider | null): void {
  provider = next;
}
