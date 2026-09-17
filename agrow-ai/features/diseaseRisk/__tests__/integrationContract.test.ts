import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("Disease Risk app integration", () => {
  it("has a Home entry and real Expo routes", () => {
    const home = readFileSync(
      resolve(process.cwd(), "features/home/components/QuickActions.tsx"),
      "utf8",
    );
    const routes = readFileSync(
      resolve(process.cwd(), "features/home/routes.ts"),
      "utf8",
    );
    expect(home).toContain('key: "diseaseRisk"');
    expect(routes).toContain('diseaseRisk: "/disease-risk"');
    expect(() =>
      readFileSync(
        resolve(process.cwd(), "app/disease-risk/index.tsx"),
        "utf8",
      ),
    ).not.toThrow();
    expect(() =>
      readFileSync(resolve(process.cwd(), "app/disease-risk/[id].tsx"), "utf8"),
    ).not.toThrow();
  });

  it("uses the authenticated backend API and never diagnosis wording", () => {
    const provider = readFileSync(
      resolve(process.cwd(), "features/diseaseRisk/api.ts"),
      "utf8",
    );
    const screen = readFileSync(
      resolve(process.cwd(), "features/diseaseRisk/DiseaseRiskScreen.tsx"),
      "utf8",
    );
    expect(provider).toContain('"/disease-risk/current"');
    expect(provider).toContain('"/disease-risk/history"');
    expect(provider).toContain('"/disease-risk/evaluate"');
    expect(screen).toContain("useGrowthTimeline(null, farmId ?? null)");
    expect(screen).toContain("evaluateRisk(farmId!, cropCycleId!)");
    expect(screen).toContain("diseaseRisk.noCropCycle");
    expect(screen).toContain('t("diseaseRisk.notDiagnosis")');
    expect(screen).not.toContain("Disease confirmed");
    expect(screen).toContain("diseaseRiskErrorMessageKey");
  });
});
