import { resolveHarvestCycleId } from "../harvestCycle";

describe("resolveHarvestCycleId", () => {
  it("uses an existing growth session when one exists", () => {
    expect(
      resolveHarvestCycleId("farm-1", "2026-08-27", "growth-session-1"),
    ).toBe("growth-session-1");
  });

  it("derives a stable cycle from a registered crop sowing date", () => {
    expect(resolveHarvestCycleId("farm-1", "2026-08-27", null)).toBe(
      "farm-farm-1-2026-08-27",
    );
  });

  it("does not invent a cycle without a sowing date", () => {
    expect(resolveHarvestCycleId("farm-1", null, null)).toBeNull();
  });
});
