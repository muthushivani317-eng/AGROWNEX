import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const screen = fs.readFileSync(
  path.join(root, "features/growth/screens/GrowthMonitorScreen.tsx"),
  "utf8",
);
const english = fs.readFileSync(
  path.join(root, "localization/locales/en.ts"),
  "utf8",
);
const tamil = fs.readFileSync(
  path.join(root, "localization/locales/ta.ts"),
  "utf8",
);
const timelineItem = fs.readFileSync(
  path.join(root, "features/growth/components/TimelineItem.tsx"),
  "utf8",
);
const stageScreen = fs.readFileSync(
  path.join(root, "features/growth/screens/CropStageTrackingScreen.tsx"),
  "utf8",
);

describe("Growth Monitor presentation contract", () => {
  it("handles farm loading, refresh failures, comparison loading and picker errors", () => {
    expect(screen).toContain("farmQuery.isLoading || farmQuery.isError");
    expect(screen).toContain("if (refreshLock.current) return");
    expect(screen).toContain("stageQuery.refetch()");
    expect(screen).toContain('view === "compare" && historyQuery.isError');
    expect(screen).toContain('view === "compare" && historyQuery.isLoading');
    expect(screen).toContain('sessionImages.length >= 2 ? null');
    expect(screen).toContain('timelineQuery.error.status === 404');
    expect(screen).toContain('t("growth.captureFailed")');
    expect(screen).toContain('t("growth.deleteFailed")');
    expect(screen).toContain('Pressable as AgPressable');
    expect(screen).not.toContain('<AgOfflineBanner');
  });
  it("keeps all working farmer actions in the redesigned screen", () => {
    expect(screen).toContain('onPick("camera")');
    expect(screen).toContain('onPick("gallery")');
    expect(screen).toContain('router.push("/growth/stage"');
    expect(screen).toContain("useGrowthTimeline");
    expect(screen).toContain("useGrowthHistory");
    expect(screen).toContain("useUploadGrowth");
    expect(screen).toContain("useDeleteGrowthImage");
  });

  it("provides accessible tabs and a meaningful capture guide", () => {
    expect(screen).toContain('accessibilityRole="tab"');
    expect(screen).toContain("accessibilityState={{ selected }}");
    expect(screen).toContain(
      'accessibilityLabel={t("growth.captureGuideAlt")}',
    );
    expect(screen).toContain("growth-capture-field.png");
  });

  it("uses explicit high-contrast text for actions, tabs, and light surfaces", () => {
    expect(screen).toContain('ink: "#101713"');
    expect(screen).toContain("style={styles.tabText}");
    expect(screen).toContain("backgroundColor: GROWTH_COLORS.action");
    expect(screen).not.toContain("styles.whiteText");
    expect(timelineItem.match(/<AgBadge\n\s+light/g)).toHaveLength(2);
    expect(screen.match(/<AgEmptyState\n\s+light/g)).toHaveLength(3);
  });

  it("includes the new interface copy in English and Tamil", () => {
    for (const locale of [english, tamil]) {
      expect(locale).toContain("journalEyebrow:");
      expect(locale).toContain("takeGrowthPhoto:");
      expect(locale).toContain("timelineHeading:");
      expect(locale).toContain("observationDisclaimer:");
      expect(locale).toContain("updateStage:");
    }
  });

  it("keeps stage tracking readable and provides a path to create its first crop cycle", () => {
    expect(stageScreen).toContain("<FarmSelector");
    expect(stageScreen).toContain("light");
    expect(stageScreen).toContain("resolveHarvestCycleId(");
    expect(stageScreen).toContain("`/farm/${selected.id}/edit`");
    expect(stageScreen).toContain('title={t("harvestReadiness.startCycle")}');
  });
});
