import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const screen = fs.readFileSync(
  path.join(root, "features/growth/screens/GrowthMonitorScreen.tsx"),
  "utf8",
);

describe("Groundnut growth-stage calendar warning", () => {
  it("shows a non-blocking warning while keeping farmer review explicit", () => {
    expect(screen).toContain("result.stageComparison?.mismatch");
    expect(screen).toContain('Alert.alert(');
    expect(screen).toContain('t("growth.stageMismatchMessage")');
    expect(screen).toContain("resetUpload()");
    expect(screen).toContain("useGroundnutStageDecision");
    expect(screen).toContain('saveGroundnutStage("correct", stage)');
    expect(screen).toContain('t("growth.groundnutStageSaved"');
    expect(screen).toContain("consumeGroundnutGrowthPhoto()");
    expect(screen).toContain("readDiseaseImageBase64(picked.uri)");
  });
});
