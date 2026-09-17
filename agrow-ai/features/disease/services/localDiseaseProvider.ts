import type { DiseaseReport, DiseaseReportSummary } from "../types";
import { DiseaseError, type DiseaseProvider } from "./diseaseProvider";
import { diseaseStorage } from "./diseaseStorage";

/** Offline disease-history provider backed by the user-scoped MMKV cache. */
function toSummary(report: DiseaseReport): DiseaseReportSummary {
  return {
    id: report.id,
    crop: report.crop,
    disease: report.disease,
    confidence: report.confidence,
    severity: report.severity,
    imageUrl: report.imageUrl,
    needsExpertReview: report.needsExpertReview,
    testMode: report.testMode,
    verificationLevel: report.verificationLevel,
    createdAt: report.createdAt,
  };
}

export const localDiseaseProvider: DiseaseProvider = {
  async listReports(
    farmId?: string | null,
    unassignedOnly = false,
  ): Promise<DiseaseReportSummary[]> {
    return diseaseStorage
      .all()
      .filter((report) =>
        unassignedOnly
          ? report.farmId === null
          : !farmId || report.farmId === farmId,
      )
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .map(toSummary);
  },

  async getReport(id: string): Promise<DiseaseReport> {
    const report = diseaseStorage.get(id);
    if (!report) throw new DiseaseError("not_found", "Report not found");
    return report;
  },

  async deleteReport(id: string): Promise<void> {
    diseaseStorage.remove(id);
  },
};
