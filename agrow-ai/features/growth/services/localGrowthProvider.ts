import { uuid } from '@/utils/id';

import type {
  GrowthImage,
  GrowthSession,
  GrowthSessionDetail,
  GrowthTimeline,
  TimelineEntry,
  UploadGrowthInput,
  UploadResult,
} from '../types';
import { GrowthError, type GrowthProvider } from './growthProvider';
import { growthStorage } from './growthStorage';
import { deriveRisk, imageToTimelineEntry, mockGrowthAnalysis } from './mockGrowth';

/**
 * Offline growth provider. Persists images/sessions in MMKV and returns the
 * deterministic mock analysis, so the monitor and timeline work in development
 * without a backend. Never used when a verified backend is configured.
 */
function buildTimeline(sessionId: string): TimelineEntry[] {
  const images = [...growthStorage.imagesForSession(sessionId)].sort(
    (a, b) => a.weekNumber - b.weekNumber || a.capturedAt.localeCompare(b.capturedAt),
  );
  let previousHealth: number | null = null;
  const entries: TimelineEntry[] = [];
  for (const image of images) {
    entries.push(imageToTimelineEntry(image, previousHealth));
    previousHealth = image.analysis?.healthScore ?? previousHealth;
  }
  return entries;
}

export const localGrowthProvider: GrowthProvider = {
  async upload(input: UploadGrowthInput): Promise<UploadResult> {
    const crop = input.crop ?? null;
    let session =
      (input.sessionId ? growthStorage.getSession(input.sessionId) : null) ??
      growthStorage.findActiveSession(input.farmId, crop);

    const now = new Date().toISOString();
    if (!session) {
      session = {
        id: uuid(),
        farmId: input.farmId,
        crop,
        variety: input.variety ?? null,
        title: null,
        sowingDate: null,
        status: 'active',
        currentGrowthStage: 'unknown',
        latestHealthScore: null,
        latestRiskLevel: null,
        imageCount: 0,
        createdAt: now,
        updatedAt: now,
      };
    }

    const existing = growthStorage.imagesForSession(session.id);
    const hasPrevious = existing.length > 0;
    const analysis = mockGrowthAnalysis(input, hasPrevious);
    const weekNumber = existing.length + 1;

    const image: GrowthImage = {
      id: uuid(),
      sessionId: session.id,
      farmId: input.farmId,
      imageUrl: input.imageUri,
      thumbnailUrl: null,
      captureMethod: input.captureMethod,
      capturedAt: now,
      weekNumber,
      latitude: input.latitude ?? null,
      longitude: input.longitude ?? null,
      weatherSnapshot: null,
      imageQuality: null,
      notes: input.notes ?? null,
      createdAt: now,
      analysis,
    };
    growthStorage.upsertImage(image);

    const previousHealth =
      existing.sort((a, b) => b.capturedAt.localeCompare(a.capturedAt))[0]?.analysis
        ?.healthScore ?? null;
    const timelineEntry = imageToTimelineEntry(image, previousHealth);

    const updatedSession: GrowthSession = {
      ...session,
      crop: session.crop ?? crop,
      variety: session.variety ?? input.variety ?? null,
      currentGrowthStage: analysis.growthStage,
      latestHealthScore: analysis.healthScore,
      latestRiskLevel: deriveRisk(analysis),
      imageCount: existing.length + 1,
      updatedAt: now,
    };
    growthStorage.upsertSession(updatedSession);

    return { session: updatedSession, image, timelineEntry, stageComparison: null };
  },

  async history(
    sessionId?: string | null,
    farmId?: string | null,
  ): Promise<GrowthImage[]> {
    const images = sessionId
      ? growthStorage.imagesForSession(sessionId)
      : growthStorage.allImages();
    return farmId ? images.filter((image) => image.farmId === farmId) : images;
  },

  async timeline(
    sessionId?: string | null,
    farmId?: string | null,
  ): Promise<GrowthTimeline> {
    const session = sessionId
      ? growthStorage.getSession(sessionId)
      : growthStorage.latestSession(farmId);
    if (!session) {
      throw new GrowthError('growth_session_not_found', 'No growth session yet.');
    }
    return { session, timeline: buildTimeline(session.id) };
  },

  async latest(): Promise<GrowthImage | null> {
    return growthStorage.allImages()[0] ?? null;
  },

  async session(id: string): Promise<GrowthSessionDetail> {
    const session = growthStorage.getSession(id);
    if (!session) {
      throw new GrowthError('growth_session_not_found', 'Growth session not found.');
    }
    return {
      ...session,
      images: growthStorage.imagesForSession(id),
      timeline: buildTimeline(id),
    };
  },

  async deleteImage(id: string): Promise<void> {
    growthStorage.removeImage(id);
  },
};
