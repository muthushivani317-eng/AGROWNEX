import type { ApiSoilScan, SoilScan } from "../types";
export function mapSoilScan(dto: ApiSoilScan): SoilScan {
  return {
    id: dto.id ?? `${dto.farm_id}:${dto.generated_at}`,
    farmId: dto.farm_id,
    aoiVerified: dto.aoi_verified,
    aoiGeojson: dto.aoi_geojson ?? null,
    generatedAt: dto.generated_at,
    providerStates: dto.provider_states ?? {},
    provenance: dto.provenance ?? {},
    indicators: dto.indicators.map((item) => ({
      code: item.code,
      status: item.status,
      evidenceClass: item.evidence_class,
      value: item.value,
      explanationCode: item.explanation_code,
      details: item.details,
      samplingPoints: item.sampling_points.map((point) => ({
        zoneId: point.zone_id,
        longitude: point.longitude,
        latitude: point.latitude,
        source: point.source,
        reference: point.reference ?? null,
        reason: point.reason ?? "spatial_variability_zone",
        quality: point.quality ?? "usable",
        sampleData: point.sample_data,
      })),
      sources: item.sources ?? [],
      observationTimestamps: item.observation_timestamps ?? [],
      missingEvidence: item.missing_evidence ?? [],
    })),
    samplingPlan: dto.sampling_plan
      ? {
          id: dto.sampling_plan.id,
          status: dto.sampling_plan.status,
          createdAt: dto.sampling_plan.created_at,
          scope: dto.sampling_plan.scope,
          points: dto.sampling_plan.points.map((point) => ({
            zoneId: point.zone_id,
            longitude: point.longitude,
            latitude: point.latitude,
            source: point.source,
            reference: point.reference ?? null,
            reason: point.reason ?? "spatial_variability_zone",
            quality: point.quality ?? "usable",
            sampleData: point.sample_data,
          })),
        }
      : null,
  };
}
