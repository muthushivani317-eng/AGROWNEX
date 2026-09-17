import {
  buildRecommendations,
  corroborate,
  worstSeverity,
  type Observation,
  type SoilRef,
} from "../services/nutrientEngine";

function obs(overrides: Partial<Observation> = {}): Observation {
  return {
    primary: "nitrogen",
    secondary: null,
    visualConfidence: 68,
    severity: "moderate",
    affectedArea: "widespread",
    ...overrides,
  };
}

const soil = (
  macro: Record<string, string>,
  micros: string[] = [],
): SoilRef => ({
  hasData: true,
  macroRatings: macro,
  deficientMicronutrients: micros,
});

describe("nutrientEngine (client mirror of the backend Nutrient Engine)", () => {
  it("reports not_confirmed when there is no visual finding", () => {
    const a = corroborate(obs({ primary: null, visualConfidence: 20 }));
    expect(a.status).toBe("not_confirmed");
    expect(a.primaryDeficiency).toBeNull();
    expect(a.needsTest).toBe(true);
  });

  it('is only "possible" from a photo alone (no corroboration)', () => {
    const a = corroborate(obs({ visualConfidence: 68 }));
    expect(a.status).toBe("possible");
    expect(a.needsTest).toBe(true);
  });

  it("is not_confirmed at low confidence", () => {
    expect(corroborate(obs({ visualConfidence: 40 })).status).toBe(
      "not_confirmed",
    );
  });

  it("confirms when soil measures the nutrient as low", () => {
    const a = corroborate(obs({ primary: "nitrogen" }), {
      soil: soil({ nitrogen: "low" }),
    });
    expect(a.soilSupports).toBe(true);
    expect(a.confidence).toBeGreaterThanOrEqual(75);
    expect(a.status).toBe("confirmed");
  });

  it("contradicts when soil measures the nutrient as high", () => {
    const a = corroborate(obs({ primary: "nitrogen" }), {
      soil: soil({ nitrogen: "high" }),
    });
    expect(a.soilSupports).toBe(false);
    expect(a.status).not.toBe("confirmed");
  });

  it("corroborates a macro deficiency with satellite low vigor", () => {
    const a = corroborate(obs({ primary: "nitrogen" }), {
      satellite: { hasData: true, vegetationHealth: "low", lowVigor: true },
    });
    expect(a.satelliteSupports).toBe(true);
    expect(a.status).toBe("confirmed");
  });

  it("corroborates nitrogen with heavy-rain leaching", () => {
    const a = corroborate(obs({ primary: "nitrogen" }), {
      weather: { hasData: true, heavyRain: true },
    });
    expect(a.weatherSupports).toBe(true);
    expect(a.status).toBe("confirmed");
  });

  it("confirms a micronutrient when the soil card shows it deficient", () => {
    const a = corroborate(obs({ primary: "zinc" }), {
      soil: soil({}, ["zinc"]),
    });
    expect(a.soilSupports).toBe(true);
    expect(a.status).toBe("confirmed");
    expect(a.needsTest).toBe(false);
  });

  it("recommends a test for a micronutrient with no soil data", () => {
    const a = corroborate(obs({ primary: "zinc" }));
    expect(a.status).toBe("possible");
    expect(a.needsTest).toBe(true);
  });

  it("lowers confidence and asks for an expert on a disease conflict", () => {
    const a = corroborate(obs({ primary: "nitrogen" }), {
      diseaseConflict: true,
    });
    expect(a.diseaseConflict).toBe(true);
    expect(a.needsExpert).toBe(true);
    expect(a.status).toBe("not_confirmed"); // 68 - 20 = 48
  });

  it("never reports 100% certainty from a photo", () => {
    const a = corroborate(obs({ visualConfidence: 99 }), {
      soil: soil({ nitrogen: "low" }),
    });
    expect(a.confidence).toBeLessThanOrEqual(99);
  });

  describe("buildRecommendations (generic codes only, no brands)", () => {
    it("gives generic nutrient advice when confirmed", () => {
      const a = corroborate(obs({ primary: "nitrogen" }), {
        soil: soil({ nitrogen: "low" }),
      });
      const codes = buildRecommendations(a).map((r) => r.code);
      expect(codes).toContain("nutrient.rec.nitrogen.deficiency");
      expect(
        buildRecommendations(a).every((r) =>
          r.code.startsWith("nutrient.rec."),
        ),
      ).toBe(true);
    });

    it("does not recommend an uncorroborated secondary deficiency", () => {
      const a = corroborate(
        obs({ primary: "nitrogen", secondary: "magnesium" }),
        {
          soil: soil({ nitrogen: "low" }),
        },
      );
      expect(buildRecommendations(a).map((r) => r.code)).not.toContain(
        "nutrient.rec.magnesium.deficiency",
      );
    });

    it("does not expose a nutrient action for visual-only evidence", () => {
      const a = corroborate(obs({ primary: "nitrogen" }));
      const codes = buildRecommendations(a).map((r) => r.code);
      expect(codes).not.toContain("nutrient.rec.nitrogen.deficiency");
      expect(codes).toContain("nutrient.rec.test.soil_test");
    });

    it("advises a soil test when not confirmed", () => {
      const a = corroborate(obs({ primary: null, visualConfidence: 20 }));
      const codes = buildRecommendations(a).map((r) => r.code);
      expect(codes).toContain("nutrient.rec.general.not_confirmed");
      expect(codes).toContain("nutrient.rec.test.soil_test");
    });

    it("recommends an expert on conflict", () => {
      const a = corroborate(obs({ primary: "nitrogen" }), {
        diseaseConflict: true,
      });
      expect(buildRecommendations(a).map((r) => r.code)).toContain(
        "nutrient.rec.expert.consult",
      );
    });

    it("worstSeverity ranks the highest, null for empty", () => {
      const a = corroborate(obs({ primary: "nitrogen", severity: "severe" }), {
        soil: soil({ nitrogen: "low" }),
      });
      expect(worstSeverity(buildRecommendations(a))).toBe("critical");
      expect(worstSeverity([])).toBeNull();
    });
  });
});
