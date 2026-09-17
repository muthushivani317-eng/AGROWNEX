import type {
  GrowthAnalysis,
  RiskLevel,
  TimelineEntry,
  UploadGrowthInput,
} from '../types';
import type { GrowthImage } from '../types';

/** Deterministic offline growth analysis (mirrors the backend mock provider). */
export function mockGrowthAnalysis(
  input: UploadGrowthInput,
  hasPrevious: boolean,
): GrowthAnalysis {
  const tamil = input.language === 'ta';
  return {
    growthStage: 'vegetative',
    plantVigor: 'good',
    healthScore: 78,
    confidence: 70,
    leafColorObservations: tamil
      ? ['இலைகள் பச்சையாக உள்ளன']
      : ['Leaves are healthy green'],
    visibleAbnormalities: tamil
      ? ['சில இலைகளில் மஞ்சள்']
      : ['Slight yellowing on a few leaves'],
    changesFromPrevious: hasPrevious
      ? tamil
        ? ['முந்தைய வாரத்தை விட உயரம் அதிகரித்துள்ளது']
        : ['Taller than last week']
      : [],
    recommendations: tamil
      ? ['தொடர்ந்து நீர்ப்பாசனம் செய்யவும்']
      : ['Continue regular irrigation'],
    diseaseResult: null,
    nutrientResult: null,
    needsExpertReview: false,
    growthSummaryTamil: 'பயிர் நல்ல வளர்ச்சியில் உள்ளது. இது டெமோ பதில்.',
    growthSummaryEnglish: 'The crop is growing well and looks healthy. This is a demo response.',
    modelUsed: 'mock-gemini-growth',
  };
}

export function deriveRisk(analysis: GrowthAnalysis): RiskLevel {
  const health = analysis.healthScore;
  if (analysis.needsExpertReview || (health != null && health < 40)) return 'high';
  if ((health != null && health < 65) || analysis.visibleAbnormalities.length > 0) {
    return 'moderate';
  }
  return 'low';
}

/** Build a timeline entry from a stored image (used by the local provider). */
export function imageToTimelineEntry(
  image: GrowthImage,
  previousHealth: number | null,
): TimelineEntry {
  const analysis = image.analysis;
  const health = analysis?.healthScore ?? null;
  const delta =
    health != null && previousHealth != null ? health - previousHealth : null;
  return {
    id: `tl-${image.id}`,
    sessionId: image.sessionId,
    imageId: image.id,
    weekNumber: image.weekNumber,
    growthStage: analysis?.growthStage ?? 'unknown',
    healthScore: health,
    healthDelta: delta,
    riskLevel: analysis ? deriveRisk(analysis) : 'low',
    summary: analysis?.growthSummaryEnglish ?? analysis?.growthSummaryTamil ?? null,
    recordedAt: image.capturedAt,
    imageUrl: image.imageUrl,
    thumbnailUrl: image.thumbnailUrl,
  };
}
