jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `mem-${++n}` };
});

import {
  draftsToMemories,
  generateSummaries,
  linkMemories,
  mergeDrafts,
  seasonForMonth,
  seasonYear,
  withLinks,
} from '../services/memoryEngine';
import type { MemoryEventDraft } from '../types';

function draft(over: Partial<MemoryEventDraft> = {}): MemoryEventDraft {
  return {
    sourceModule: 'disease',
    eventType: 'disease_diagnosed',
    occurredAt: '2026-07-01T06:00:00.000Z',
    summary: 'memory.event.disease_diagnosed',
    importance: 'high',
    observation: 'observed',
    confidence: 90,
    crop: 'paddy',
    location: null,
    sourceRef: 'r1',
    params: {},
    detail: null,
    tags: ['disease'],
    ...over,
  };
}

describe('memoryEngine — season derivation', () => {
  it('maps months to Tamil-Nadu seasons', () => {
    expect(seasonForMonth(7)).toBe('kharif');
    expect(seasonForMonth(11)).toBe('rabi');
    expect(seasonForMonth(1)).toBe('rabi');
    expect(seasonForMonth(4)).toBe('summer');
  });

  it('assigns Jan/Feb to the previous agricultural year', () => {
    expect(seasonYear(2026, 1)).toBe(2025);
    expect(seasonYear(2026, 7)).toBe(2026);
  });
});

describe('memoryEngine — merge + build', () => {
  it('collapses duplicate drafts (same key) and keeps the strongest lead', () => {
    const weak = draft({ importance: 'low', confidence: 50, sourceRef: 'same' });
    const strong = draft({ importance: 'critical', confidence: 95, sourceRef: 'same' });
    const merged = mergeDrafts([weak, strong]);
    expect(merged).toHaveLength(1);
    expect(merged[0].drafts).toHaveLength(2);
    expect(merged[0].lead.importance).toBe('critical');
  });

  it('builds sample memories with a derived season and isSample flag', () => {
    const memories = draftsToMemories('farm-1', [draft()]);
    expect(memories).toHaveLength(1);
    expect(memories[0].isSample).toBe(true);
    expect(memories[0].season).toBe('kharif');
    expect(memories[0].seasonYear).toBe(2026);
    expect(memories[0].importanceScore).toBe(75);
  });
});

describe('memoryEngine — summaries', () => {
  it('groups by season and year with counts + top importance', () => {
    const memories = draftsToMemories('farm-1', [
      draft({ sourceRef: 'a', occurredAt: '2026-07-01T06:00:00.000Z', importance: 'critical' }),
      draft({
        sourceModule: 'soil',
        eventType: 'soil_report_uploaded',
        summary: 'memory.event.soil_report_uploaded',
        importance: 'medium',
        sourceRef: 'b',
        occurredAt: '2026-08-01T06:00:00.000Z',
      }),
    ]);
    const { seasons, years } = generateSummaries(memories);
    const kharif = seasons.find((s) => s.periodKey === '2026-kharif');
    expect(kharif?.eventCount).toBe(2);
    expect(kharif?.importance).toBe('critical');
    expect(kharif?.params?.disease_count).toBe(1);
    expect(years[0].periodKey).toBe('2026');
    expect(years[0].eventCount).toBe(2);
  });
});

describe('memoryEngine — links', () => {
  it('relates cross-module memories in the same crop + season', () => {
    const memories = draftsToMemories('farm-1', [
      draft({ sourceRef: 'd1', occurredAt: '2026-07-01T06:00:00.000Z' }),
      draft({
        sourceModule: 'soil',
        eventType: 'soil_report_uploaded',
        summary: 'memory.event.soil_report_uploaded',
        sourceRef: 's1',
        occurredAt: '2026-07-05T06:00:00.000Z',
      }),
    ]);
    const links = linkMemories(memories);
    expect(links.some((l) => l.linkType === 'relates')).toBe(true);
  });

  it('resolves an expert resolution back to a disease diagnosis', () => {
    const memories = draftsToMemories('farm-1', [
      draft({ sourceRef: 'd1', occurredAt: '2026-07-01T06:00:00.000Z' }),
      draft({
        sourceModule: 'experts',
        eventType: 'expert_consultation_resolved',
        summary: 'memory.event.expert_consultation_resolved',
        importance: 'medium',
        sourceRef: 'e1',
        occurredAt: '2026-07-10T06:00:00.000Z',
      }),
    ]);
    const links = linkMemories(memories);
    expect(links.some((l) => l.linkType === 'resolves')).toBe(true);
  });

  it('attaches each memory its own links via withLinks', () => {
    const memories = withLinks(
      draftsToMemories('farm-1', [
        draft({ sourceModule: 'growth', eventType: 'growth_tracked', sourceRef: 'g1', occurredAt: '2026-07-01T06:00:00.000Z' }),
        draft({ sourceModule: 'growth', eventType: 'growth_tracked', sourceRef: 'g2', occurredAt: '2026-07-08T06:00:00.000Z' }),
      ]),
    );
    // The later growth memory follows the earlier one.
    const withFollows = memories.find((m) => m.links.some((l) => l.linkType === 'follows'));
    expect(withFollows).toBeDefined();
  });
});
