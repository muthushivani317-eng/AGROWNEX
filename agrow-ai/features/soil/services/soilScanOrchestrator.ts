import type { SatelliteDashboard } from "@/features/satellite/types";

export const SATELLITE_REFRESH_AFTER_MS = 7 * 24 * 60 * 60 * 1000;

export type SoilScanPhase =
  | "idle"
  | "checking_satellite"
  | "refreshing_satellite"
  | "refreshing_waterlogging"
  | "preparing_soil";

/** A successful refresh may reuse an older cloud-free acquisition, so freshness
 * is based on when AgrowAI processed the session, not the scene capture date. */
export function hasRecentUsableSatellite(
  dashboard: SatelliteDashboard,
  nowMs = Date.now(),
): boolean {
  const session = dashboard.session;
  if (!dashboard.hasData || session?.status !== "available") return false;
  const hasNumericEvidence = [
    session.ndvi,
    session.ndre,
    session.evi,
    session.ndmi,
  ].some((value) => typeof value === "number" && Number.isFinite(value));
  const processedAt = Date.parse(session.createdAt);
  return (
    hasNumericEvidence &&
    Number.isFinite(processedAt) &&
    nowMs - processedAt >= 0 &&
    nowMs - processedAt < SATELLITE_REFRESH_AFTER_MS
  );
}

interface SoilScanDependencies<T> {
  getDashboard: () => Promise<SatelliteDashboard>;
  refreshSatellite: (hasPolygon: boolean) => Promise<unknown>;
  refreshWaterlogging?: () => Promise<unknown>;
  runSoilScan: () => Promise<T>;
  onPhaseChange?: (phase: SoilScanPhase) => void;
  nowMs?: number;
}

export async function runSoilScanWithSatellite<T>({
  getDashboard,
  refreshSatellite,
  refreshWaterlogging,
  runSoilScan,
  onPhaseChange,
  nowMs = Date.now(),
}: SoilScanDependencies<T>): Promise<T> {
  onPhaseChange?.("checking_satellite");
  const dashboard = await getDashboard();
  if (!hasRecentUsableSatellite(dashboard, nowMs)) {
    onPhaseChange?.("refreshing_satellite");
    await refreshSatellite(dashboard.hasPolygon);
  }
  if (dashboard.hasPolygon && refreshWaterlogging) {
    onPhaseChange?.("refreshing_waterlogging");
    await refreshWaterlogging();
  }
  onPhaseChange?.("preparing_soil");
  return runSoilScan();
}
