import { apiToAnalysis } from "../services/nutrientMapper";

it("maps abstention evidence and keeps expert verification false", () => {
  const result = apiToAnalysis({
    primary_deficiency: null,
    secondary_deficiency: null,
    status: "not_confirmed",
    confidence: 42,
    severity: "unknown",
    affected_area: null,
    disease_conflict: true,
    needs_test: true,
    needs_expert: true,
    soil_reference: null,
    satellite_reference: null,
    weather_reference: null,
    explanation_tamil: null,
    explanation_english: null,
    result_code: "abstained",
    confidence_band: "low",
    evidence_observed: [],
    evidence_missing: ["soil_or_tissue_evidence"],
    conflicts: ["disease_or_differential_ambiguity"],
    abstention_reason: "conflicting_evidence",
    suggested_next_evidence: ["expert_review"],
    expert_verified: false,
  });
  expect(result.resultCode).toBe("abstained");
  expect(result.primaryDeficiency).toBeNull();
  expect(result.expertVerified).toBe(false);
});
