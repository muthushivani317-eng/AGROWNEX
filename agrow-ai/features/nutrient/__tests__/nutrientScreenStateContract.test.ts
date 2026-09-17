import fs from "node:fs";
import path from "node:path";

const readScreen = (name: string) =>
  fs.readFileSync(path.join(__dirname, "..", "screens", name), "utf8");

describe("nutrient screen state contract", () => {
  it("keeps offline ownership at the app shell and shows a farm loading state", () => {
    const entry = readScreen("NutrientAnalysisScreen.tsx");
    const history = readScreen("NutrientHistoryScreen.tsx");

    expect(entry).not.toContain("<AgOfflineBanner");
    expect(history).not.toContain("<AgOfflineBanner");
    expect(entry).toContain('testID="nutrient-farms-loading"');
    expect(entry).toContain("farmsLoading ?");
  });

  it("supports pull-to-refresh on history and report screens", () => {
    const history = readScreen("NutrientHistoryScreen.tsx");
    const result = readScreen("NutrientResultScreen.tsx");

    for (const source of [history, result]) {
      expect(source).toContain("<RefreshControl");
      expect(source).toContain("query.isRefetching");
      expect(source).toContain("query.refetch()");
    }
  });

  it("does not display stale history rows over a refresh failure", () => {
    const history = readScreen("NutrientHistoryScreen.tsx");
    expect(history).toContain("query.isError ? [] : (query.data ?? [])");
    expect(history.indexOf("query.isError ?")).toBeLessThan(
      history.indexOf("reports.length === 0"),
    );
  });
});
