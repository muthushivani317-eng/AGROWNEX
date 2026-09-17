import { uuid } from "@/utils/id";

import { DEFAULT_PAGE_SIZE } from "../constants";
import type {
  Paginated,
  SoilDashboard,
  SoilHistoryEntry,
  SoilProfile,
  SoilRecommendation,
  SoilReport,
  SoilReportInput,
  SoilSource,
  SoilValues,
} from "../types";
import { assess, buildRecommendations } from "./soilEngine";
import { SoilError, type SoilProvider } from "./soilProvider";
import { soilStorage } from "./soilStorage";

/**
 * Local, offline Soil Intelligence provider. Stores farmer-uploaded reports in MMKV
 * and runs the same deterministic Soil Engine as the backend, so the module works in
 * dev / without a backend. It never fabricates a value — unknowns stay null and the
 * dashboard reports "no data" honestly (docs/PRODUCT_RULES.md).
 */
const SOURCE_CONFIDENCE: Record<SoilSource, number> = {
  lab: 95,
  soil_health_card: 90,
  government: 80,
  self: 70,
  satellite: 60,
  farm_registration: 30,
  estimate: 25,
};

const VALUE_KEYS: (keyof SoilValues)[] = [
  "ph",
  "organicCarbon",
  "nitrogen",
  "phosphorus",
  "potassium",
  "sulphur",
  "ecSalinity",
  "waterHoldingCapacity",
];

function mergedValues(farmId: string): SoilValues {
  const reports = soilStorage.localReports(farmId);
  const values: SoilValues = {};
  // Apply oldest → newest so the most recent measured value wins.
  for (const report of [...reports].reverse()) {
    const r = report.result;
    if (!r) continue;
    const record = r as unknown as Record<string, number | null>;
    for (const key of VALUE_KEYS) {
      const v = record[key];
      if (v !== undefined && v !== null)
        (values as Record<string, unknown>)[key] = v;
    }
    if (r.drainage) values.drainage = r.drainage as SoilValues["drainage"];
    if (r.micronutrients) {
      values.micronutrients = {
        ...(values.micronutrients ?? {}),
        ...r.micronutrients,
      };
    }
  }
  return values;
}

function toHistory(report: SoilReport): SoilHistoryEntry {
  const r = report.result;
  return {
    id: report.id,
    farmId: report.farmId,
    reportId: report.id,
    testDate: report.testDate,
    ph: r?.ph ?? null,
    organicCarbon: r?.organicCarbon ?? null,
    nitrogen: r?.nitrogen ?? null,
    phosphorus: r?.phosphorus ?? null,
    potassium: r?.potassium ?? null,
    source: report.source,
    confidence: report.confidence,
    recordedAt: report.createdAt,
  };
}

function syntheticProfile(
  farmId: string,
  values: SoilValues,
  report: SoilReport,
  soilTypeHint?: string | null,
): SoilProfile {
  return {
    id: `local-${farmId}`,
    farmId,
    soilType: soilTypeHint ?? null,
    latitude: null,
    longitude: null,
    ph: values.ph ?? null,
    organicCarbon: values.organicCarbon ?? null,
    nitrogen: values.nitrogen ?? null,
    phosphorus: values.phosphorus ?? null,
    potassium: values.potassium ?? null,
    micronutrients: values.micronutrients ?? null,
    ecSalinity: values.ecSalinity ?? null,
    waterHoldingCapacity: values.waterHoldingCapacity ?? null,
    drainage: values.drainage ?? null,
    source: report.source,
    confidence: report.confidence,
    lastTestDate: report.testDate,
    updatedAt: report.createdAt,
  };
}

export const localSoilProvider: SoilProvider = {
  async remoteEstimation() {
    return {
      status: "remote_estimation_unavailable",
      reason: "development_provider_has_no_real_remote_data",
      estimates: [],
    };
  },
  async dashboard(
    farmId: string,
    soilTypeHint?: string | null,
  ): Promise<SoilDashboard> {
    const reports = soilStorage.localReports(farmId);
    if (reports.length === 0) {
      const values: SoilValues = {};
      return {
        farmId,
        hasData: false,
        messageCode: "soil.status.no_data",
        profile: null,
        assessment: assess(values),
        recommendations: buildRecommendations(values, soilTypeHint),
        latestReport: null,
        indicatorEvidence: [],
        overallStatus: "insufficient_data",
        laboratoryEquivalent: false,
      };
    }
    const values = mergedValues(farmId);
    const assessment = assess(values);
    return {
      farmId,
      hasData:
        assessment.hasAnyValue || assessment.deficientMicronutrients.length > 0,
      messageCode: null,
      profile: syntheticProfile(farmId, values, reports[0], soilTypeHint),
      assessment,
      recommendations: buildRecommendations(values, soilTypeHint),
      latestReport: reports[0],
      indicatorEvidence: [],
      overallStatus: "assessed",
      laboratoryEquivalent: false,
    };
  },

  async latest(farmId: string): Promise<SoilReport> {
    const reports = soilStorage.localReports(farmId);
    if (reports.length === 0) {
      throw new SoilError("soil_data_unavailable", "No soil data yet.");
    }
    return reports[0];
  },

  async history(
    farmId: string,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<SoilHistoryEntry>> {
    const rows = soilStorage.localReports(farmId).map(toHistory);
    const start = (page - 1) * pageSize;
    return {
      items: rows.slice(start, start + pageSize),
      page,
      pageSize,
      total: rows.length,
      totalPages: Math.max(1, Math.ceil(rows.length / pageSize)),
    };
  },

  async recommendations(
    farmId: string,
    soilTypeHint?: string | null,
  ): Promise<SoilRecommendation[]> {
    return buildRecommendations(mergedValues(farmId), soilTypeHint);
  },

  async submitReport(input: SoilReportInput): Promise<SoilReport> {
    const source = input.source ?? "self";
    const now = new Date().toISOString();
    const v = input.values;
    const report: SoilReport = {
      id: uuid(),
      farmId: input.farmId,
      source,
      reportUrl: input.reportUrl ?? null,
      thumbnailUrl: input.thumbnailUrl ?? null,
      labName: input.labName ?? null,
      testDate: input.testDate ?? null,
      notes: input.notes ?? null,
      status: "processed",
      confidence: SOURCE_CONFIDENCE[source] ?? 50,
      createdAt: now,
      result: {
        ph: v.ph ?? null,
        organicCarbon: v.organicCarbon ?? null,
        nitrogen: v.nitrogen ?? null,
        phosphorus: v.phosphorus ?? null,
        potassium: v.potassium ?? null,
        sulphur: v.sulphur ?? null,
        ecSalinity: v.ecSalinity ?? null,
        waterHoldingCapacity: v.waterHoldingCapacity ?? null,
        drainage: v.drainage ?? null,
        micronutrients: v.micronutrients ?? null,
      },
    };
    soilStorage.addLocalReport(input.farmId, report);
    return report;
  },
};
