import type { SupportedLanguage } from '@/types';

import type {
  ApiDiseaseReport,
  ApiDiseaseReportSummary,
  DiseaseReport,
  DiseaseReportSummary,
  WeatherSnapshot,
} from '../types';

const toLang = (v: string): SupportedLanguage => (v === 'en' ? 'en' : 'ta');

function toSnapshot(raw: Record<string, unknown> | null): WeatherSnapshot | null {
  if (!raw) return null;
  return {
    condition: raw.condition as string | undefined,
    temperatureC: (raw.temperature_c as number | null | undefined) ?? null,
    humidityPct: (raw.humidity_pct as number | null | undefined) ?? null,
    windSpeedKmh: (raw.wind_speed_kmh as number | null | undefined) ?? null,
    fetchedAt: raw.fetched_at as string | undefined,
  };
}

export function apiToReport(dto: ApiDiseaseReport): DiseaseReport {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    crop: dto.crop,
    cropConfidence: dto.crop_confidence,
    disease: dto.disease,
    confidence: dto.confidence,
    severity: dto.severity,
    symptoms: dto.symptoms ?? [],
    causes: dto.causes ?? [],
    recommendations: dto.recommendations ?? [],
    prevention: dto.prevention ?? [],
    conventionalCategoryEnglish: dto.conventional_category_english ?? null,
    conventionalCategoryTamil: dto.conventional_category_tamil ?? null,
    visibleParts: dto.visible_parts ?? [],
    needsExpertReview: dto.needs_expert_review,
    explanationTamil: dto.explanation_tamil,
    explanationEnglish: dto.explanation_english,
    imageUrl: dto.image_url,
    privateImageAvailable: dto.private_image_available === true,
    modelUsed: dto.model_used,
    testMode: dto.test_mode ?? null,
    verificationLevel: dto.verification_level ?? null,
    weatherSnapshot: toSnapshot(dto.weather_snapshot),
    latitude: dto.latitude,
    longitude: dto.longitude,
    language: toLang(dto.language),
    createdAt: dto.created_at,
  };
}

export function apiToSummary(dto: ApiDiseaseReportSummary): DiseaseReportSummary {
  return {
    id: dto.id,
    crop: dto.crop,
    disease: dto.disease,
    confidence: dto.confidence,
    severity: dto.severity,
    imageUrl: dto.image_url,
    privateImageAvailable: dto.private_image_available === true,
    needsExpertReview: dto.needs_expert_review,
    testMode: dto.test_mode ?? null,
    verificationLevel: dto.verification_level ?? null,
    createdAt: dto.created_at,
  };
}
