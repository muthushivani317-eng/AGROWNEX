import { httpClient } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

/**
 * Client for backend/app/modules/organic_mvp's plot / crop-cycle / plan
 * endpoints (the blueprint's "Conversion Plan"). Same module as
 * organicReadinessApi.ts -- raw payloads, not the { success, data }
 * envelope, so this goes through httpClient directly.
 *
 * Note: plot/crop-cycle capture here does NOT yet include baseline soil
 * values or a target buyer category -- the blueprint asks for both, but the
 * backend's OrganicPlot/OrganicCropCycle models don't have those columns
 * yet. Adding them is a schema migration, flagged for a separate decision
 * rather than done silently here.
 */

export interface OrganicPlot {
  id: string;
  name: string;
  area_hectares: number | null;
  trial_only: boolean;
  notice: string | null;
}

export interface OrganicPlotInput {
  name: string;
  area_hectares?: number | null;
  boundary_geojson?: Record<string, unknown> | null;
}

export interface OrganicCropCycle {
  id: string;
  crop_id: string;
  sowing_date: string | null;
  expected_harvest_start: string | null;
  expected_harvest_end: string | null;
  expected_quantity_kg: number | null;
}

export interface OrganicCropCycleInput {
  crop_id: string;
  sowing_date?: string | null;
  expected_harvest_start?: string | null;
  expected_harvest_end?: string | null;
  expected_quantity_kg?: number | null;
}

export interface OrganicScheduledTask {
  id: string;
  /** Week number (1 = season start, 6 = sowing) for the common plan; null for crop-specific plans. */
  week: number | null;
  due_on: string;
  title_ta: string;
  body_ta: string;
  title_en: string | null;
  body_en: string | null;
  status: string;
}

export interface OrganicCropCyclePlan {
  /** "ready", or "needs_sowing_date" when the cycle has no sowing date yet. */
  status: "ready" | "needs_sowing_date";
  /** "reviewed_template" for a crop-specific plan, else the common plan version. */
  source: string;
  notice_ta: string;
  notice_en: string;
  tasks: OrganicScheduledTask[];
}

export interface OrganicTodayTask {
  id: string;
  due_on: string;
  title_ta: string;
  body_ta: string;
  title_en: string | null;
  body_en: string | null;
  is_overdue: boolean;
}

export interface OrganicTodayTaskResponse {
  tasks: OrganicTodayTask[];
}

export const organicConversionApi = {
  async listPlots(farmId: string): Promise<OrganicPlot[]> {
    const res = await httpClient.get<OrganicPlot[]>(endpoints.organicMvp.plots(farmId));
    return res.data;
  },
  async createPlot(
    farmId: string,
    input: OrganicPlotInput,
  ): Promise<{ id: string; notice: string | null }> {
    const res = await httpClient.post<{ id: string; notice: string | null }>(
      endpoints.organicMvp.plots(farmId),
      input,
    );
    return res.data;
  },
  async listCropCycles(plotId: string): Promise<OrganicCropCycle[]> {
    const res = await httpClient.get<OrganicCropCycle[]>(
      endpoints.organicMvp.cropCycles(plotId),
    );
    return res.data;
  },
  async createCropCycle(
    plotId: string,
    input: OrganicCropCycleInput,
  ): Promise<{ id: string; status: string }> {
    const res = await httpClient.post<{ id: string; status: string }>(
      endpoints.organicMvp.cropCycles(plotId),
      input,
    );
    return res.data;
  },
  async getCropCyclePlan(cycleId: string): Promise<OrganicCropCyclePlan> {
    const res = await httpClient.get<OrganicCropCyclePlan>(
      endpoints.organicMvp.cropCyclePlan(cycleId),
    );
    return res.data;
  },
  /** Today's (and any overdue, unresolved) organic task(s) for a farm --
   * across every activated crop-cycle plan, not just one cycle. See
   * `organic_mvp/router.py::today_task` for the "never hide unresolved work"
   * rationale (mirrors daily_task's own cooldown behaviour).
   */
  async getTodayTasks(farmId: string): Promise<OrganicTodayTaskResponse> {
    const res = await httpClient.get<OrganicTodayTaskResponse>(
      endpoints.organicMvp.todayTask(farmId),
    );
    return res.data;
  },
};
