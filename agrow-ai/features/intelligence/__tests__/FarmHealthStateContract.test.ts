import fs from "node:fs";
import path from "node:path";

const readScreen = (name: string) =>
  fs.readFileSync(path.resolve(__dirname, "..", "screens", name), "utf8");

describe("Farm Health loading and recovery contract", () => {
  it("shows farm-loading UI before evaluating the dashboard query", () => {
    const dashboard = readScreen("IntelligenceDashboardScreen.tsx");

    expect(dashboard).toContain('testID="farm-health-farm-loading"');
    expect(dashboard).toContain("farmsLoading || query.isLoading ?");
  });

  it("uses the app shell as the single offline-banner owner", () => {
    for (const screen of [
      "IntelligenceDashboardScreen.tsx",
      "IntelligenceHistoryScreen.tsx",
      "IntelligenceReportScreen.tsx",
    ]) {
      expect(readScreen(screen)).not.toContain("<AgOfflineBanner");
    }
  });

  it("keeps pull-to-refresh and retry paths on all server-data views", () => {
    for (const screen of [
      "IntelligenceDashboardScreen.tsx",
      "IntelligenceHistoryScreen.tsx",
      "IntelligenceReportScreen.tsx",
    ]) {
      const source = readScreen(screen);
      expect(source).toContain("<RefreshControl");
      expect(source).toContain("query.isRefetching");
      expect(source).toContain("query.refetch()");
      expect(source).toContain("<AgErrorState");
    }
  });

  it("does not show stale history rows over a refresh error", () => {
    const history = readScreen("IntelligenceHistoryScreen.tsx");
    expect(history).toContain("query.isError ? [] : (query.data?.items ?? [])");
  });
});
