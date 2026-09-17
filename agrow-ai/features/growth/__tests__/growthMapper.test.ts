import {
  apiToAnalysis,
  apiToImage,
  apiToSession,
  apiToTimeline,
  apiToTimelineEntry,
  apiToUploadResult,
} from '../services/growthMapper';
import type {
  ApiGrowthImage,
  ApiGrowthSession,
  ApiTimelineEntry,
  ApiUploadResult,
} from '../types';

const apiSession: ApiGrowthSession = {
  id: 's1',
  farm_id: 'f1',
  crop: 'paddy',
  variety: 'ADT-43',
  title: null,
  sowing_date: '2026-06-01',
  status: 'active',
  current_growth_stage: 'vegetative',
  latest_health_score: 78,
  latest_risk_level: 'low',
  image_count: 2,
  created_at: '2026-06-01T00:00:00Z',
  updated_at: '2026-06-15T00:00:00Z',
};

const apiImage: ApiGrowthImage = {
  id: 'img1',
  session_id: 's1',
  farm_id: 'f1',
  image_url: 'https://r2/growth/1.jpg',
  thumbnail_url: null,
  capture_method: 'camera',
  captured_at: '2026-06-08T00:00:00Z',
  week_number: 2,
  latitude: 9.9,
  longitude: 78.1,
  weather_snapshot: { condition: 'Clear', temperature_c: 31, humidity_pct: 60 },
  image_quality: { width: 800, height: 800 },
  notes: 'looks green',
  created_at: '2026-06-08T00:00:00Z',
  analysis: {
    growth_stage: 'vegetative',
    plant_vigor: 'good',
    health_score: 78,
    confidence: 70,
    leaf_color_observations: ['green'],
    visible_abnormalities: ['slight yellowing'],
    changes_from_previous: ['taller'],
    recommendations: ['irrigate'],
    disease_result: null,
    nutrient_result: null,
    needs_expert_review: false,
    growth_summary_tamil: 'வளர்ச்சி நன்று',
    growth_summary_english: 'growing well',
    model_used: 'mock-gemini-growth',
  },
};

describe('apiToAnalysis', () => {
  it('maps snake_case to camelCase', () => {
    const a = apiToAnalysis(apiImage.analysis);
    expect(a?.growthStage).toBe('vegetative');
    expect(a?.plantVigor).toBe('good');
    expect(a?.healthScore).toBe(78);
    expect(a?.changesFromPrevious).toEqual(['taller']);
  });

  it('returns null for a missing analysis', () => {
    expect(apiToAnalysis(null)).toBeNull();
  });
});

describe('apiToImage', () => {
  it('maps image + nested analysis + weather snapshot', () => {
    const image = apiToImage(apiImage);
    expect(image.sessionId).toBe('s1');
    expect(image.weekNumber).toBe(2);
    expect(image.weatherSnapshot?.temperatureC).toBe(31);
    expect(image.analysis?.growthSummaryTamil).toBe('வளர்ச்சி நன்று');
  });
});

describe('apiToTimelineEntry', () => {
  it('maps a timeline entry', () => {
    const dto: ApiTimelineEntry = {
      id: 'tl1',
      session_id: 's1',
      image_id: 'img1',
      week_number: 2,
      growth_stage: 'vegetative',
      health_score: 78,
      health_delta: 15,
      risk_level: 'low',
      summary: 'growing well',
      recorded_at: '2026-06-08T00:00:00Z',
      image_url: 'https://r2/growth/1.jpg',
      thumbnail_url: null,
    };
    const entry = apiToTimelineEntry(dto);
    expect(entry.weekNumber).toBe(2);
    expect(entry.healthDelta).toBe(15);
    expect(entry.riskLevel).toBe('low');
  });
});

describe('apiToSession', () => {
  it('maps a session', () => {
    const s = apiToSession(apiSession);
    expect(s.crop).toBe('paddy');
    expect(s.currentGrowthStage).toBe('vegetative');
    expect(s.latestHealthScore).toBe(78);
    expect(s.imageCount).toBe(2);
  });
});

describe('apiToTimeline & apiToUploadResult', () => {
  it('maps a timeline envelope', () => {
    const timeline = apiToTimeline({ session: apiSession, timeline: [] });
    expect(timeline.session.id).toBe('s1');
    expect(timeline.timeline).toEqual([]);
  });

  it('maps an upload result', () => {
    const dto: ApiUploadResult = {
      session: apiSession,
      image: apiImage,
      timeline_entry: {
        id: 'tl1',
        session_id: 's1',
        image_id: 'img1',
        week_number: 2,
        growth_stage: 'vegetative',
        health_score: 78,
        health_delta: null,
        risk_level: 'low',
        summary: null,
        recorded_at: '2026-06-08T00:00:00Z',
        image_url: null,
        thumbnail_url: null,
      },
    };
    const result = apiToUploadResult(dto);
    expect(result.session.id).toBe('s1');
    expect(result.image.id).toBe('img1');
    expect(result.timelineEntry.imageId).toBe('img1');
  });
});
