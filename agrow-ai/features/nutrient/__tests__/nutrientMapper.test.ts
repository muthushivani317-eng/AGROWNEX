import {
  apiToAnalysis,
  apiToHistoryEntry,
  apiToRecommendation,
  apiToReport,
} from '../services/nutrientMapper';
import type {
  ApiNutrientAnalysis,
  ApiNutrientHistoryEntry,
  ApiNutrientReport,
} from '../types';

const apiAnalysis: ApiNutrientAnalysis = {
  primary_deficiency: 'nitrogen',
  secondary_deficiency: null,
  status: 'possible',
  confidence: 68,
  severity: 'moderate',
  affected_area: 'widespread',
  disease_conflict: false,
  needs_test: true,
  needs_expert: false,
  soil_reference: { has_data: true },
  satellite_reference: null,
  weather_reference: null,
  explanation_tamil: 'ta',
  explanation_english: 'en',
};

const apiReport: ApiNutrientReport = {
  id: 'r1',
  farm_id: 'f1',
  crop: 'paddy',
  image_url: 'https://r2/leaf.jpg',
  thumbnail_url: null,
  capture_date: '2026-07-12',
  provider: 'gemini',
  model_used: 'gemini-x',
  status: 'analyzed',
  language: 'ta',
  latitude: 10.7,
  longitude: 79.1,
  weather_snapshot: null,
  analysis: apiAnalysis,
  symptoms: ['yellowing', 'older_leaf_first'],
  recommendations: [
    {
      category: 'nutrient',
      code: 'nutrient.rec.nitrogen.deficiency',
      nutrient: 'nitrogen',
      severity: 'warning',
      priority: 'medium',
    },
  ],
  created_at: '2026-07-12T06:00:00Z',
};

describe('nutrientMapper', () => {
  it('maps a report envelope to the camelCase domain shape', () => {
    const r = apiToReport(apiReport);
    expect(r.farmId).toBe('f1');
    expect(r.imageUrl).toBe('https://r2/leaf.jpg');
    expect(r.language).toBe('ta');
    expect(r.symptoms).toEqual(['yellowing', 'older_leaf_first']);
    expect(r.recommendations[0].code).toBe('nutrient.rec.nitrogen.deficiency');
    expect(r.analysis?.primaryDeficiency).toBe('nitrogen');
    expect(r.analysis?.needsTest).toBe(true);
  });

  it('preserves honest nulls (never fabricated)', () => {
    const r = apiToReport({
      ...apiReport,
      analysis: { ...apiAnalysis, primary_deficiency: null, status: 'not_confirmed' },
      symptoms: [],
      recommendations: [],
    });
    expect(r.analysis?.primaryDeficiency).toBeNull();
    expect(r.analysis?.status).toBe('not_confirmed');
    expect(r.symptoms).toEqual([]);
    expect(r.recommendations).toEqual([]);
  });

  it('maps analysis and recommendation directly', () => {
    expect(apiToAnalysis(apiAnalysis).affectedArea).toBe('widespread');
    expect(
      apiToRecommendation({
        category: 'test',
        code: 'nutrient.rec.test.soil_test',
        nutrient: null,
        severity: 'warning',
        priority: 'medium',
      }).code,
    ).toBe('nutrient.rec.test.soil_test');
  });

  it('maps a history entry', () => {
    const h: ApiNutrientHistoryEntry = {
      id: 'h1',
      farm_id: 'f1',
      report_id: 'r1',
      crop: 'paddy',
      primary_deficiency: 'nitrogen',
      status: 'possible',
      confidence: 68,
      severity: 'moderate',
      recorded_at: '2026-07-12T06:00:00Z',
    };
    const entry = apiToHistoryEntry(h);
    expect(entry.reportId).toBe('r1');
    expect(entry.primaryDeficiency).toBe('nitrogen');
    expect(entry.recordedAt).toBe('2026-07-12T06:00:00Z');
  });
});
