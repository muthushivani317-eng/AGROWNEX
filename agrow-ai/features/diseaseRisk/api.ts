import { api } from "@/services/apiClient";
import { uuid } from "@/utils/id";
import type { ApiDiseaseRiskAlert, DiseaseRiskAlert } from "./types";

const mapAlert = (x: ApiDiseaseRiskAlert): DiseaseRiskAlert => ({
  id: x.id,
  farmId: x.farm_id,
  crop: x.crop,
  diseaseKey: x.disease_key,
  status: x.status,
  riskLevel: x.risk_level,
  confidence: x.confidence,
  weatherFactors: x.weather_factors,
  weatherSource: x.weather_source,
  cropStage: x.crop_stage,
  generatedAt: x.generated_at,
  validUntil: x.valid_until,
  ruleVersion: x.rule_version,
  ruleVerificationStatus: x.rule_verification_status,
  farmerMessageKey: x.farmer_message_key,
  missingInputs: x.missing_inputs,
  acknowledgedAt: x.acknowledged_at,
  cached: x.cached,
});

export async function getCurrentRisk(
  farmId: string,
): Promise<DiseaseRiskAlert | null> {
  const value = await api.get<ApiDiseaseRiskAlert | null>(
    "/disease-risk/current",
    { params: { farm_id: farmId } },
  );
  return value ? mapAlert(value) : null;
}

export async function evaluateRisk(
  farmId: string,
  cropCycleId: string,
): Promise<DiseaseRiskAlert> {
  const value = await api.post<ApiDiseaseRiskAlert>("/disease-risk/evaluate", {
    farm_id: farmId,
    crop_cycle_id: cropCycleId,
    idempotency_key: uuid(),
  });
  return mapAlert(value);
}

export async function getRiskHistory(
  farmId: string,
): Promise<DiseaseRiskAlert[]> {
  const value = await api.get<{ items: ApiDiseaseRiskAlert[] }>(
    "/disease-risk/history",
    { params: { farm_id: farmId } },
  );
  return value.items.map(mapAlert);
}

export async function getRisk(id: string): Promise<DiseaseRiskAlert> {
  return mapAlert(await api.get<ApiDiseaseRiskAlert>(`/disease-risk/${id}`));
}
