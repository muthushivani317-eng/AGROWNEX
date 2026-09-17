import {
  deriveRisk,
  imageToTimelineEntry,
  mockGrowthAnalysis,
} from '../services/mockGrowth';
import type { GrowthAnalysis, GrowthImage, UploadGrowthInput } from '../types';

function analysis(overrides: Partial<GrowthAnalysis> = {}): GrowthAnalysis {
  return {
    growthStage: 'vegetative',
    plantVigor: 'good',
    healthScore: 78,
    confidence: 70,
    leafColorObservations: [],
    visibleAbnormalities: [],
    changesFromPrevious: [],
    recommendations: [],
    diseaseResult: null,
    nutrientResult: null,
    needsExpertReview: false,
    growthSummaryTamil: 'ta',
    growthSummaryEnglish: 'en',
    modelUsed: 'mock',
    ...overrides,
  };
}

function image(id: string, week: number, a: GrowthAnalysis): GrowthImage {
  return {
    id,
    sessionId: 'sess',
    farmId: 'f1',
    imageUrl: `uri-${id}`,
    thumbnailUrl: null,
    captureMethod: 'camera',
    capturedAt: `2026-06-0${week}T00:00:00Z`,
    weekNumber: week,
    latitude: null,
    longitude: null,
    weatherSnapshot: null,
    imageQuality: null,
    notes: null,
    createdAt: `2026-06-0${week}T00:00:00Z`,
    analysis: a,
  };
}

const baseInput: UploadGrowthInput = {
  imageBase64: 'x',
  mimeType: 'image/jpeg',
  imageUri: 'file://x',
  farmId: 'f1',
  language: 'ta',
  captureMethod: 'camera',
};

describe('mockGrowthAnalysis', () => {
  it('is Tamil-first when language is ta', () => {
    const a = mockGrowthAnalysis(baseInput, false);
    expect(a.growthStage).toBe('vegetative');
    expect(a.growthSummaryTamil).toBeTruthy();
    expect(a.changesFromPrevious).toEqual([]); // no previous → no comparison
  });

  it('adds comparison notes when a previous photo exists', () => {
    const a = mockGrowthAnalysis({ ...baseInput, language: 'en' }, true);
    expect(a.changesFromPrevious.length).toBeGreaterThan(0);
  });
});

describe('deriveRisk', () => {
  it('is low for a healthy plant with no abnormalities', () => {
    expect(deriveRisk(analysis({ healthScore: 80, visibleAbnormalities: [] }))).toBe(
      'low',
    );
  });

  it('is moderate when abnormalities are present', () => {
    expect(
      deriveRisk(analysis({ healthScore: 80, visibleAbnormalities: ['yellowing'] })),
    ).toBe('moderate');
  });

  it('is moderate for a middling health score', () => {
    expect(deriveRisk(analysis({ healthScore: 55 }))).toBe('moderate');
  });

  it('is high when review is needed or health is very low', () => {
    expect(deriveRisk(analysis({ needsExpertReview: true }))).toBe('high');
    expect(deriveRisk(analysis({ healthScore: 30 }))).toBe('high');
  });
});

describe('imageToTimelineEntry', () => {
  it('computes the health delta vs the previous week', () => {
    const entry = imageToTimelineEntry(image('a', 2, analysis({ healthScore: 78 })), 60);
    expect(entry.weekNumber).toBe(2);
    expect(entry.healthDelta).toBe(18);
    expect(entry.imageUrl).toBe('uri-a');
  });

  it('has a null delta for the first week', () => {
    const entry = imageToTimelineEntry(image('a', 1, analysis()), null);
    expect(entry.healthDelta).toBeNull();
  });
});
