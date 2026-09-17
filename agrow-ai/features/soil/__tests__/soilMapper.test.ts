import {
  apiToDashboard,
  apiToReport,
  reportInputToApi,
} from "../services/soilMapper";
import type { ApiSoilDashboard, ApiSoilReport } from "../types";

const apiReport: ApiSoilReport = {
  id: "r1",
  farm_id: "f1",
  source: "soil_health_card",
  report_url: "https://r2/card.jpg",
  thumbnail_url: null,
  lab_name: null,
  test_date: "2026-07-01",
  notes: null,
  status: "processed",
  confidence: 90,
  created_at: "2026-07-12T06:00:00Z",
  result: {
    ph: 5.2,
    organic_carbon: 0.3,
    nitrogen: 200,
    phosphorus: null,
    potassium: null,
    sulphur: null,
    ec_salinity: null,
    water_holding_capacity: null,
    drainage: null,
    micronutrients: null,
  },
};

describe("soilMapper", () => {
  it("maps a soil report to camelCase", () => {
    const r = apiToReport(apiReport);
    expect(r.farmId).toBe("f1");
    expect(r.reportUrl).toBe("https://r2/card.jpg");
    expect(r.result?.ph).toBe(5.2);
    expect(r.result?.organicCarbon).toBe(0.3);
  });

  it("maps a dashboard incl. assessment + recommendations", () => {
    const dto: ApiSoilDashboard = {
      farm_id: "f1",
      has_data: true,
      message_code: null,
      profile: {
        id: "p1",
        farm_id: "f1",
        soil_type: "Sandy loam",
        latitude: null,
        longitude: null,
        ph: 5.2,
        organic_carbon: 0.3,
        nitrogen: 200,
        phosphorus: null,
        potassium: null,
        micronutrients: null,
        ec_salinity: null,
        water_holding_capacity: null,
        drainage: null,
        source: "soil_health_card",
        confidence: 90,
        last_test_date: "2026-07-01",
        updated_at: "2026-07-12T06:00:00Z",
      },
      assessment: {
        ph_class: "strongly_acidic",
        organic_carbon: "low",
        nitrogen: "low",
        phosphorus: "unknown",
        potassium: "unknown",
        salinity: "unknown",
        deficient_micronutrients: [],
        has_any_value: true,
      },
      recommendations: [
        {
          category: "ph",
          code: "soil.rec.ph.strongly_acidic",
          parameter: "ph",
          rating: "strongly_acidic",
          severity: "critical",
          priority: "high",
          value: 5.2,
          unit: null,
        },
      ],
      latest_report: apiReport,
    };
    const dash = apiToDashboard(dto);
    expect(dash.hasData).toBe(true);
    expect(dash.profile?.soilType).toBe("Sandy loam");
    expect(dash.assessment?.phClass).toBe("strongly_acidic");
    expect(dash.recommendations[0].code).toBe("soil.rec.ph.strongly_acidic");
    expect(dash.latestReport?.id).toBe("r1");
  });

  it("maps a report input to a snake_case body", () => {
    const body = reportInputToApi({
      farmId: "f1",
      source: "lab",
      testDate: "2026-07-01",
      values: { ph: 6.5, organicCarbon: 0.8, ecSalinity: 1.2 },
    });
    expect(body.farm_id).toBe("f1");
    expect(body.source).toBe("lab");
    const values = body.values as Record<string, unknown>;
    expect(values.ph).toBe(6.5);
    expect(values.organic_carbon).toBe(0.8);
    expect(values.ec_salinity).toBe(1.2);
    expect(values.phosphorus).toBeNull();
  });
});

it("preserves per-indicator evidence and remote-unavailable status", () => {
  const mapped = apiToDashboard({
    farm_id: "f1",
    has_data: false,
    message_code: "soil.status.remote_estimation_unavailable",
    profile: null,
    assessment: null,
    recommendations: [],
    latest_report: null,
    indicator_evidence: [
      {
        indicator: "ph",
        value: 6.7,
        unit: "pH",
        evidence_type: "laboratory_measured",
        collection_method: "laboratory_report",
        collected_at: "2026-08-01",
        source_reference: "LAB-1",
        spatial_coverage: "sample",
        confidence: 95,
        uncertainty_low: null,
        uncertainty_high: null,
        verification_state: "verified",
        freshness: "current",
        status: "assessed",
        report_reference: "report-1",
      },
    ],
    overall_status: "remote_estimation_unavailable",
    laboratory_equivalent: false,
  });

  expect(mapped.indicatorEvidence[0]).toMatchObject({
    indicator: "ph",
    evidenceType: "laboratory_measured",
    unit: "pH",
  });
  expect(mapped.overallStatus).toBe("remote_estimation_unavailable");
  expect(mapped.laboratoryEquivalent).toBe(false);
});
