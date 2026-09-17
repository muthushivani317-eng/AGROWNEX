import {
  fallbackHarvestReadiness,
  mapHarvestReadiness,
} from "../harvestReadiness";
import { isMissingGrowthSession } from "../harvestReadinessErrors";
import { ApiError } from "@/types";
import fs from "node:fs";
import path from "node:path";

it("fails closed without criteria and never contains a generated date", () => {
  const result = fallbackHarvestReadiness();
  expect(result.state).toBe("no_verified_readiness_rule");
  expect(result.missing).toContain("verified_readiness_criteria");
  expect(result).not.toHaveProperty("harvestDate");
});

it("maps backend evidence without inventing a harvest date", () => {
  const result = mapHarvestReadiness({
    id: "r1",
    farm_id: "f1",
    crop_cycle_id: "c1",
    state: "insufficient_data",
    version: 1,
    criteria_version: null,
    evidence_snapshot: {
      reliability: "low",
      missing: ["confirmed_stage", "live_weather"],
      evidence_observed: ["planting_date"],
      conflicts: [],
      farmer_confirmation_required: false,
    },
    pending_sync: false,
    updated_at: "2026-08-15T00:00:00Z",
  });
  expect(result.missing).toEqual(["confirmed_stage", "live_weather"]);
  expect(result.cached).toBe(false);
  expect(result).not.toHaveProperty("harvestDate");
});

it("treats a missing first growth session as setup, not a connection error", () => {
  expect(
    isMissingGrowthSession(
      new ApiError({
        status: 404,
        message: "No growth session",
        errorCode: "growth_session_not_found",
      }),
    ),
  ).toBe(true);
  expect(
    isMissingGrowthSession(
      new ApiError({
        status: 0,
        message: "Offline",
        errorCode: "network_error",
      }),
    ),
  ).toBe(false);
});

it("uses farm details as the cycle fallback and only offers setup for missing essentials", () => {
  const screen = fs.readFileSync(
    path.resolve(__dirname, "../screens/HarvestReadinessScreen.tsx"),
    "utf8",
  );

  expect(screen).toContain("useFarm(farms.selected?.id)");
  expect(screen).toContain("resolveHarvestCycleId(");
  expect(screen).toContain("farmDetail.data?.crop && farmDetail.data?.sowingDate");
  expect(screen).toContain("harvestReadiness.startCycle");
  expect(screen).toContain("/farm/${farms.selected!.id}/edit");
});
