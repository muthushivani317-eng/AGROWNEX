import type { SoilIndicatorEvidence, SoilSource } from "../types";

export function evidenceLabelKey(
  evidence: SoilIndicatorEvidence | undefined,
  fallbackSource?: SoilSource,
): string {
  switch (evidence?.evidenceType) {
    case "laboratory_measured":
    case "lab_measured":
      return "soil.evidenceLabMeasured";
    case "government_record":
    case "report_extracted":
      return "soil.evidenceReportExtracted";
    case "farmer_observed":
    case "user_entered":
      return "soil.evidenceUserEntered";
    case "remote_sensing_estimate":
    case "remote_estimate":
      return "soil.evidenceRemoteEstimate";
    case "model_estimate":
      return "soil.evidenceModelEstimate";
    default:
      if (fallbackSource === "lab") return "soil.evidenceLabMeasured";
      if (fallbackSource === "soil_health_card")
        return "soil.evidenceReportExtracted";
      if (fallbackSource === "self") return "soil.evidenceUserEntered";
      if (fallbackSource === "satellite") return "soil.evidenceRemoteEstimate";
      if (fallbackSource === "estimate") return "soil.evidenceModelEstimate";
      return "soil.evidenceUnavailable";
  }
}
