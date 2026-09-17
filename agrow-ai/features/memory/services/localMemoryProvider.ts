import { logger } from '@/lib/logger';

import { nutrientStorage } from '@/features/nutrient/services/nutrientStorage';
import { satelliteStorage } from '@/features/satellite/services/satelliteStorage';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  FarmMemory,
  MemoryDashboard,
  MemoryEventDraft,
  MemoryHistoryFilter,
  MemoryRebuildResult,
  MemorySummaryBundle,
  Paginated,
} from '../types';
import { draftsToMemories, generateSummaries, withLinks } from './memoryEngine';
import { MemoryError, type MemoryProvider } from './memoryProvider';
import { memoryStorage } from './memoryStorage';

/**
 * Local, offline Farm Memory provider. On rebuild it aggregates whatever the sibling
 * module stores (Nutrient, Satellite) hold in MMKV — each read is **guarded**, exactly
 * like the backend sources, so one missing module simply contributes no memory and is
 * never fabricated. The client engine mirror then merges duplicates, derives seasons,
 * builds summaries and links. Memories are flagged ``isSample`` so a locally-derived
 * record is never mistaken for a verified one.
 */
function guard<T>(name: string, fn: () => T[]): T[] {
  try {
    return fn();
  } catch (err) {
    logger.warn('memory', `local source '${name}' failed; skipping`, err);
    return [];
  }
}

function nutrientDrafts(farmId: string): MemoryEventDraft[] {
  return nutrientStorage
    .localReports(farmId)
    .flatMap((r): MemoryEventDraft[] => {
      const a = r.analysis;
      if (!a || (a.status !== 'confirmed' && a.status !== 'possible') || !a.primaryDeficiency) {
        return [];
      }
      const importance =
        a.status === 'confirmed' && a.severity === 'severe'
          ? 'high'
          : a.status === 'confirmed'
            ? 'medium'
            : 'low';
      return [
        {
          sourceModule: 'nutrient',
          eventType: 'nutrient_deficiency_detected',
          occurredAt: r.createdAt,
          summary: 'memory.event.nutrient_deficiency_detected',
          importance,
          observation: a.status === 'confirmed' ? 'observed' : 'inferred',
          confidence: a.confidence,
          crop: r.crop,
          location: null,
          sourceRef: r.id,
          params: { nutrient: a.primaryDeficiency, status: a.status, severity: a.severity },
          detail: null,
          tags: ['nutrient', a.primaryDeficiency, a.status],
        },
      ];
    });
}

function satelliteDrafts(farmId: string): MemoryEventDraft[] {
  return satelliteStorage
    .localSessions(farmId)
    .filter((s) => s.status === 'available')
    .map((s): MemoryEventDraft => {
      const declining =
        s.trend === 'declining' ||
        ['bare', 'very_low', 'low'].includes(s.vegetationHealth ?? '') ||
        ['moderate', 'severe'].includes(s.stressLevel ?? '');
      return {
        sourceModule: 'satellite',
        eventType: declining ? 'satellite_vegetation_decline' : 'satellite_scan',
        occurredAt: s.captureDate ?? s.createdAt,
        summary: declining
          ? 'memory.event.satellite_vegetation_decline'
          : 'memory.event.satellite_scan',
        importance: declining ? (s.stressLevel === 'severe' ? 'high' : 'medium') : 'low',
        observation: 'inferred',
        confidence: s.confidence,
        crop: null,
        location: null,
        sourceRef: s.id,
        params: { vegetation_health: s.vegetationHealth, trend: s.trend, ndvi: s.ndvi },
        detail: null,
        tags: ['satellite', declining ? 'decline' : 'scan'],
      };
    });
}

function buildMemories(farmId: string): FarmMemory[] {
  const drafts = [
    ...guard('nutrient', () => nutrientDrafts(farmId)),
    ...guard('satellite', () => satelliteDrafts(farmId)),
  ];
  const memories = draftsToMemories(farmId, drafts);
  return withLinks(memories);
}

function applyFilter(items: FarmMemory[], filter?: MemoryHistoryFilter): FarmMemory[] {
  return items.filter((m) => {
    if (filter?.sourceModule && m.sourceModule !== filter.sourceModule) return false;
    if (filter?.season && m.season !== filter.season) return false;
    if (filter?.crop && m.crop !== filter.crop) return false;
    if (filter?.importance && m.importance !== filter.importance) return false;
    if (filter?.q) {
      const q = filter.q.toLowerCase();
      const hay = `${m.eventType} ${m.summary} ${m.tags.join(' ')}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

export const localMemoryProvider: MemoryProvider = {
  async rebuild(farmId: string): Promise<MemoryRebuildResult> {
    const memories = buildMemories(farmId);
    memoryStorage.setLocalMemories(farmId, memories);
    const { seasons, years } = generateSummaries(memories);
    return {
      farmId,
      created: memories.length,
      total: memories.length,
      summaries: seasons.length + years.length,
      links: memories.reduce((n, m) => n + m.links.length, 0),
    };
  },

  async dashboard(farmId: string): Promise<MemoryDashboard> {
    const memories = memoryStorage.localMemories(farmId);
    const { seasons } = generateSummaries(memories);
    return {
      farmId,
      hasData: memories.length > 0,
      total: memories.length,
      messageCode: memories.length ? null : 'memory.status.no_memory',
      recent: memories.slice(0, 5),
      latestSummary: seasons[0] ?? null,
    };
  },

  async latest(farmId: string): Promise<FarmMemory> {
    const memory = memoryStorage.localMemories(farmId)[0];
    if (!memory) throw new MemoryError('unavailable', 'No memory yet');
    return memory;
  },

  async history(
    farmId: string,
    filter?: MemoryHistoryFilter,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<FarmMemory>> {
    const rows = applyFilter(memoryStorage.localMemories(farmId), filter);
    const start = (page - 1) * pageSize;
    return {
      items: rows.slice(start, start + pageSize),
      page,
      pageSize,
      total: rows.length,
      totalPages: Math.max(1, Math.ceil(rows.length / pageSize)),
    };
  },

  async summary(farmId: string): Promise<MemorySummaryBundle> {
    const { seasons, years } = generateSummaries(memoryStorage.localMemories(farmId));
    return { farmId, seasons, years };
  },

  async getMemory(id: string): Promise<FarmMemory> {
    const memory = memoryStorage.getLocalMemory(id);
    if (!memory) throw new MemoryError('not_found', 'Memory not found');
    return memory;
  },
};
