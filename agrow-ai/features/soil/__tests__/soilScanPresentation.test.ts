import { en } from "@/localization/locales/en";
import { ta } from "@/localization/locales/ta";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const required = [
  "checkingSatellite", "analyzingField", "refreshingWaterlogging",
  "preparingInsights", "prerequisitesTitle", "prerequisitesBody",
  "runSatellite", "runWaterlogging", "addBoundary", "estimateSoilTexture",
  "uploadSoilReport", "observedAt", "providerStatus",
] as const;

describe("soil scan presentation contract", () => {
  it("defines every actionable soil-scan string in English and Tamil", () => {
    for (const key of required) {
      expect(en.soil[key]).toEqual(expect.any(String));
      expect(ta.soil[key]).toEqual(expect.any(String));
      expect(en.soil[key]).not.toMatch(/content unavailable/i);
      expect(ta.soil[key].trim()).not.toBe("");
    }
  });

  it("exposes prerequisite actions and evidence metadata", () => {
    const screen = readFileSync(
      resolve(process.cwd(), "features/soil/screens/SoilScanScreen.tsx"),
      "utf8",
    );
    for (const route of ["/satellite", "/satellite/waterlogging", "/boundary", "/soil/upload"]) {
      expect(screen).toContain(route);
    }
    expect(screen).toContain("observationTimestamps");
    expect(screen).toContain("providerStates");
    expect(screen).toContain('title={t("soil.estimateSoilTexture")}');
    expect(screen).not.toContain('router.push(`/farm/${farmId}/edit`)');
  });
});
