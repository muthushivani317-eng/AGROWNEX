/**
 * Client mirror of the backend Farm Memory Engine (pure). Used by the local/offline
 * provider so memory works in dev / without a backend. Mirrors the backend's season
 * derivation, deterministic dedup, duplicate merging, seasonal/yearly summaries and
 * deterministic links — and, like the backend, never fabricates data.
 */
import { uuid } from '@/utils/id';

import { IMPORTANCE_ORDER, IMPORTANCE_SCORE } from '../constants';
import type {
  FarmMemory,
  MemoryEventDraft,
  MemoryImportance,
  MemoryLink,
  MemoryLinkType,
  MemorySummary,
} from '../types';

export function seasonForMonth(month: number): string {
  if ([6, 7, 8, 9, 10].includes(month)) return 'kharif';
  if ([11, 12, 1, 2].includes(month)) return 'rabi';
  if ([3, 4, 5].includes(month)) return 'summer';
  return 'unknown';
}

export function seasonYear(year: number, month: number): number {
  return month === 1 || month === 2 ? year - 1 : year;
}

function dedupKey(d: MemoryEventDraft): string {
  const date = new Date(d.occurredAt);
  const day = date.toISOString().slice(0, 10);
  const crop = (d.crop ?? '-').toLowerCase();
  const ref = d.sourceRef ?? day;
  return `${d.sourceModule}:${d.eventType}:${crop}:${ref}`;
}

interface Merged {
  key: string;
  lead: MemoryEventDraft;
  drafts: MemoryEventDraft[];
}

export function mergeDrafts(drafts: MemoryEventDraft[]): Merged[] {
  const buckets = new Map<string, MemoryEventDraft[]>();
  for (const d of drafts) {
    const key = dedupKey(d);
    const list = buckets.get(key) ?? [];
    list.push(d);
    buckets.set(key, list);
  }
  const merged: Merged[] = [];
  for (const [key, group] of buckets) {
    const lead = [...group].sort((a, b) => {
      const imp = IMPORTANCE_ORDER[b.importance] - IMPORTANCE_ORDER[a.importance];
      if (imp !== 0) return imp;
      const conf = (b.confidence ?? 0) - (a.confidence ?? 0);
      if (conf !== 0) return conf;
      return new Date(b.occurredAt).getTime() - new Date(a.occurredAt).getTime();
    })[0];
    merged.push({ key, lead, drafts: group });
  }
  merged.sort((a, b) => new Date(b.lead.occurredAt).getTime() - new Date(a.lead.occurredAt).getTime());
  return merged;
}

/** Convert merged drafts to farm memories (flagged `isSample` — offline/dev). */
export function draftsToMemories(farmId: string, drafts: MemoryEventDraft[]): FarmMemory[] {
  return mergeDrafts(drafts).map((m) => {
    const d = new Date(m.lead.occurredAt);
    return {
      id: uuid(),
      farmId,
      sourceModule: m.lead.sourceModule,
      eventType: m.lead.eventType,
      summary: m.lead.summary,
      params: m.lead.params,
      confidence: m.lead.confidence,
      importance: m.lead.importance,
      importanceScore: IMPORTANCE_SCORE[m.lead.importance],
      observation: m.lead.observation,
      season: seasonForMonth(d.getUTCMonth() + 1),
      seasonYear: seasonYear(d.getUTCFullYear(), d.getUTCMonth() + 1),
      crop: m.lead.crop,
      location: m.lead.location,
      occurredAt: m.lead.occurredAt,
      createdAt: new Date().toISOString(),
      tags: Array.from(new Set(m.lead.tags)),
      occurrences: m.drafts.length,
      links: [],
      isSample: true,
    };
  });
}

function topImportance(values: MemoryImportance[]): MemoryImportance {
  let best: MemoryImportance = 'low';
  for (const v of values) {
    if (IMPORTANCE_ORDER[v] > IMPORTANCE_ORDER[best]) best = v;
  }
  return best;
}

function dominant<T>(values: T[]): T | null {
  if (values.length === 0) return null;
  const counts = new Map<T, number>();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
}

export function generateSummaries(memories: FarmMemory[]): {
  seasons: MemorySummary[];
  years: MemorySummary[];
} {
  const bySeason = new Map<string, FarmMemory[]>();
  const byYear = new Map<number, FarmMemory[]>();
  for (const m of memories) {
    const year = m.seasonYear ?? new Date(m.occurredAt).getUTCFullYear();
    if (m.season) {
      const k = `${year}-${m.season}`;
      bySeason.set(k, [...(bySeason.get(k) ?? []), m]);
    }
    byYear.set(year, [...(byYear.get(year) ?? []), m]);
  }

  const build = (
    items: FarmMemory[],
    periodType: 'season' | 'year',
    periodKey: string,
    season: string | null,
    year: number,
  ): MemorySummary => {
    const diseaseCount = items.filter((i) => i.sourceModule === 'disease').length;
    const crop = dominant(items.map((i) => i.crop).filter(Boolean) as string[]);
    const highlights = [...items]
      .sort(
        (a, b) =>
          IMPORTANCE_ORDER[b.importance] - IMPORTANCE_ORDER[a.importance] ||
          new Date(b.occurredAt).getTime() - new Date(a.occurredAt).getTime(),
      )
      .slice(0, 3)
      .map((i) => i.id);
    return {
      id: uuid(),
      farmId: items[0].farmId,
      periodType,
      periodKey,
      season,
      year,
      crop,
      summary: 'memory.summary.period',
      params: {
        season,
        year,
        crop,
        dominant_module: dominant(items.map((i) => i.sourceModule)),
        disease_count: diseaseCount,
      },
      highlights,
      eventCount: items.length,
      importance: topImportance(items.map((i) => i.importance)),
      generatedAt: new Date().toISOString(),
    };
  };

  const seasons = [...bySeason.entries()].map(([k, items]) => {
    const [year, season] = k.split('-');
    return build(items, 'season', k, season, Number(year));
  });
  const years = [...byYear.entries()].map(([year, items]) =>
    build(items, 'year', String(year), null, year),
  );
  const sortDesc = (a: MemorySummary, b: MemorySummary) =>
    b.year - a.year || b.periodKey.localeCompare(a.periodKey);
  return { seasons: seasons.sort(sortDesc), years: years.sort(sortDesc) };
}

const RESOLVES: Record<string, string> = {
  expert_consultation_resolved: 'disease_diagnosed',
  disease_resolved: 'disease_diagnosed',
};

/** Deterministic links between memories (follows / relates / resolves). */
export function linkMemories(memories: FarmMemory[]): MemoryLink[] {
  const ordered = [...memories].sort(
    (a, b) => new Date(a.occurredAt).getTime() - new Date(b.occurredAt).getTime(),
  );
  const links: MemoryLink[] = [];
  const seen = new Set<string>();
  const add = (a: FarmMemory, b: FarmMemory, t: MemoryLinkType): void => {
    if (a.id === b.id) return;
    const sig = `${a.id}:${b.id}:${t}`;
    if (seen.has(sig)) return;
    seen.add(sig);
    links.push({ id: uuid(), fromMemoryId: a.id, toMemoryId: b.id, linkType: t });
  };

  const lastByModule = new Map<string, FarmMemory>();
  ordered.forEach((f) => {
    const prev = lastByModule.get(f.sourceModule);
    if (prev) add(f, prev, 'follows');
    lastByModule.set(f.sourceModule, f);
  });

  ordered.forEach((f, idx) => {
    if (!f.crop || !f.season) return;
    for (let j = idx - 1; j >= 0; j -= 1) {
      const g = ordered[j];
      if (
        g.crop === f.crop &&
        g.season === f.season &&
        g.seasonYear === f.seasonYear &&
        g.sourceModule !== f.sourceModule
      ) {
        add(f, g, 'relates');
        break;
      }
    }
  });

  ordered.forEach((f, idx) => {
    const target = RESOLVES[f.eventType];
    if (!target) return;
    for (let j = idx - 1; j >= 0; j -= 1) {
      const g = ordered[j];
      if (g.eventType === target && (g.crop === f.crop || !f.crop)) {
        add(f, g, 'resolves');
        break;
      }
    }
  });

  return links;
}

/** Attach the computed links to each memory (in-place mapping, pure result). */
export function withLinks(memories: FarmMemory[]): FarmMemory[] {
  const links = linkMemories(memories);
  return memories.map((m) => ({
    ...m,
    links: links.filter((l) => l.fromMemoryId === m.id || l.toMemoryId === m.id),
  }));
}
