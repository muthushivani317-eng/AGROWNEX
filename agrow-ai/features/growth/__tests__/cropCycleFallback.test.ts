import fs from "node:fs";
import path from "node:path";

it("uses the same farm-and-sowing-date cycle fallback as harvest readiness", () => {
  const screen = fs.readFileSync(
    path.resolve(__dirname, "../screens/CropStageTrackingScreen.tsx"),
    "utf8",
  );

  expect(screen).toContain("resolveHarvestCycleId(");
  expect(screen).toContain("useStageState(selected?.id, cycleId)");
  expect(screen).toContain("cropCycleId: cycleId");
  expect(screen).toContain("/farm/${selected.id}/edit");
});
