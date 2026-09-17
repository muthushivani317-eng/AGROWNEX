import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const readScreen = (name: string) =>
  readFileSync(
    resolve(process.cwd(), `features/soil/screens/${name}.tsx`),
    "utf8",
  );

describe("Soil Intelligence light-state contract", () => {
  it.each([
    "SoilDashboardScreen",
    "SoilHistoryScreen",
    "SoilRecommendationsScreen",
  ])("keeps empty and error states readable in %s", (name) => {
    const source = readScreen(name);
    for (const match of source.matchAll(/<Ag(?:Empty|Error)State[\s\S]*?\/>/g)) {
      expect(match[0]).toMatch(/\blight\b/);
    }
  });

  it("keeps saved scan errors on the light Soil palette", () => {
    expect(readScreen("SoilScanScreen")).toMatch(
      /<AgErrorState\s+light\s+onRetry/,
    );
  });

  it("uses explicit readable colors for soil-history values", () => {
    const source = readScreen("SoilHistoryScreen");
    expect(source).toContain("style={styles.primaryText}");
    expect(source).toContain("style={styles.mutedText}");
    expect(source).toContain("color: SOIL_UI.text");
    expect(source).toContain("color: SOIL_UI.muted");
  });
});
