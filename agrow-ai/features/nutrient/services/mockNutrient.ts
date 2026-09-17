import type { AnalyzeInput, NutrientReport } from "../types";
import {
  buildRecommendations,
  corroborate,
  type Observation,
} from "./nutrientEngine";

/**
 * Deterministic offline analysis, mirroring the backend mock provider + engine.
 * Lets the Nutrient screen work in development without a backend or Gemini key.
 * Safe and generic — a mild nitrogen pattern with NO corroboration, so the offline
 * verdict is honestly "possible" (never a fabricated "confirmed").
 */
export function mockNutrientReport(
  input: AnalyzeInput,
  id: string,
): NutrientReport {
  const ta = input.language === "ta";
  const observation: Observation = {
    primary: "nitrogen",
    secondary: null,
    visualConfidence: 68,
    severity: "moderate",
    affectedArea: "widespread",
  };
  // Offline has no soil/satellite/weather references to corroborate with.
  const assessment = corroborate(observation);
  const recommendations = buildRecommendations(assessment);

  return {
    id,
    farmId: input.farmId,
    crop: input.crop ?? "paddy",
    imageUrl: input.imageUri,
    thumbnailUrl: null,
    captureDate: new Date().toISOString().slice(0, 10),
    provider: "mock",
    modelUsed: "mock-nutrient-vision",
    status: "analyzed",
    language: input.language,
    latitude: input.latitude ?? null,
    longitude: input.longitude ?? null,
    weatherSnapshot: null,
    analysis: {
      primaryDeficiency: assessment.primaryDeficiency,
      secondaryDeficiency: assessment.secondaryDeficiency,
      status: assessment.status,
      confidence: assessment.confidence,
      severity: assessment.severity,
      affectedArea: assessment.affectedArea,
      diseaseConflict: assessment.diseaseConflict,
      needsTest: assessment.needsTest,
      needsExpert: assessment.needsExpert,
      soilReference: null,
      satelliteReference: null,
      weatherReference: null,
      explanationTamil: ta
        ? "பழைய இலைகள் மஞ்சளாக மாறுகின்றன — நைட்ரஜன் குறைபாட்டின் அறிகுறி. இது டெமோ பதில்; உறுதிசெய்ய மண் பரிசோதனை செய்யவும்."
        : null,
      explanationEnglish: ta
        ? null
        : "A sample yellowing pattern was observed. This is not a confirmed deficiency.",
      resultCode: "abstained",
      confidenceBand: "medium",
      evidenceObserved: ["sample_visual_pattern"],
      evidenceMissing: ["soil_or_tissue_evidence"],
      conflicts: [],
      abstentionReason: "development_sample_not_corroborated",
      suggestedNextEvidence: ["soil_or_tissue_test", "expert_review"],
      expertVerified: false,
    },
    symptoms: ["yellowing", "pale_leaf", "older_leaf_first"],
    recommendations,
    createdAt: new Date().toISOString(),
  };
}
