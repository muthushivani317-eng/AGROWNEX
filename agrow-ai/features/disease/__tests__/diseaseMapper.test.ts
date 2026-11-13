import type { ApiDiseaseReport, ApiDiseaseReportSummary } from '../types';
import { apiToReport, apiToSummary } from '../services/diseaseMapper';

const dto: ApiDiseaseReport = {
  id: 'r1',
  farm_id: 'f1',
  crop: 'paddy',
  crop_confidence: 80,
  disease: 'Leaf blast',
  confidence: 77,
  severity: 'moderate',
  symptoms: ['spots'],
  causes: ['fungus'],
  recommendations: ['prune'],
  prevention: ['rotate'],
  conventional_category_english: 'Use a protectant fungicide.',
  conventional_category_tamil: 'ஒரு பாதுகாப்பு பூஞ்சைக் கொல்லியைப் பயன்படுத்தவும்.',
  visible_parts: ['leaf'],
  needs_expert_review: true,
  explanation_tamil: 'விளக்கம்',
  explanation_english: 'explanation',
  image_url: 'https://cdn/x.jpg',
  private_image_available: true,
  thumbnail_url: null,
  model_used: 'gemini-2.5-pro',
  weather_snapshot: { condition: 'rain', temperature_c: 29, humidity_pct: 80 },
  latitude: 9.9,
  longitude: 78.1,
  language: 'ta',
  created_at: '2026-07-10T09:00:00Z',
  pest_observation: null,
};

describe('diseaseMapper', () => {
  it('maps a full report', () => {
    const report = apiToReport(dto);
    expect(report.disease).toBe('Leaf blast');
    expect(report.confidence).toBe(77);
    expect(report.severity).toBe('moderate');
    expect(report.needsExpertReview).toBe(true);
    expect(report.symptoms).toEqual(['spots']);
    expect(report.weatherSnapshot?.condition).toBe('rain');
    expect(report.weatherSnapshot?.temperatureC).toBe(29);
    expect(report.language).toBe('ta');
    expect(report.privateImageAvailable).toBe(true);
  });

  it('tolerates a null weather snapshot', () => {
    const report = apiToReport({ ...dto, weather_snapshot: null });
    expect(report.weatherSnapshot).toBeNull();
  });

  it('maps a summary', () => {
    const summary: ApiDiseaseReportSummary = {
      id: 'r1',
      crop: 'cotton',
      disease: 'Wilt',
      confidence: 60,
      severity: 'high',
      image_url: 'https://cdn/y.jpg',
      private_image_available: true,
      needs_expert_review: false,
      created_at: '2026-07-10T09:00:00Z',
      pest_observation: {
        damage_extent: 'several',
        spread_speed: 'rapid',
        review_status: 'reviewed',
        feedback: 'seek_in_person_field_assessment',
        review_timestamp: '2026-07-11T09:00:00Z',
      },
    };
    const mapped = apiToSummary(summary);
    expect(mapped.disease).toBe('Wilt');
    expect(mapped.severity).toBe('high');
    expect(mapped.privateImageAvailable).toBe(true);
    expect(mapped.pestObservation).toEqual({
      damageExtent: 'several',
      spreadSpeed: 'rapid',
      reviewStatus: 'reviewed',
      feedback: 'seek_in_person_field_assessment',
      reviewTimestamp: '2026-07-11T09:00:00Z',
    });
  });
});
