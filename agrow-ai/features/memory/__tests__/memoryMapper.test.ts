import { apiToDashboard, apiToMemory, apiToSummaryBundle } from '../services/memoryMapper';
import type { ApiFarmMemory, ApiMemoryDashboard, ApiMemorySummaryBundle } from '../types';

const apiMemory: ApiFarmMemory = {
  id: 'm1',
  farm_id: 'f1',
  source_module: 'disease',
  event_type: 'disease_diagnosed',
  summary: 'memory.event.disease_diagnosed',
  params: { disease: 'Blast' },
  confidence: 90,
  importance: 'critical',
  importance_score: 95,
  observation: 'observed',
  season: 'kharif',
  season_year: 2026,
  crop: 'paddy',
  location: 'Thanjavur',
  occurred_at: '2026-07-01T06:00:00.000Z',
  created_at: '2026-07-01T07:00:00.000Z',
  tags: ['disease', 'high'],
  occurrences: 2,
  links: [{ id: 'l1', from_memory_id: 'm1', to_memory_id: 'm2', link_type: 'relates' }],
};

describe('memoryMapper', () => {
  it('maps a memory snake_case → camelCase (and never invents fields)', () => {
    const m = apiToMemory(apiMemory);
    expect(m.farmId).toBe('f1');
    expect(m.sourceModule).toBe('disease');
    expect(m.importanceScore).toBe(95);
    expect(m.seasonYear).toBe(2026);
    expect(m.observation).toBe('observed');
    expect(m.occurrences).toBe(2);
    expect(m.links[0]).toEqual({
      id: 'l1',
      fromMemoryId: 'm1',
      toMemoryId: 'm2',
      linkType: 'relates',
    });
    expect(m.isSample).toBe(false); // an API memory is verified, not a sample
  });

  it('maps the dashboard with recent memories and a latest summary', () => {
    const dto: ApiMemoryDashboard = {
      farm_id: 'f1',
      has_data: true,
      total: 3,
      message_code: null,
      recent: [apiMemory],
      latest_summary: {
        id: 's1',
        farm_id: 'f1',
        period_type: 'season',
        period_key: '2026-kharif',
        season: 'kharif',
        year: 2026,
        crop: 'paddy',
        summary: 'memory.summary.period',
        params: { disease_count: 1 },
        highlights: ['m1'],
        event_count: 3,
        importance: 'critical',
        generated_at: '2026-08-01T00:00:00.000Z',
      },
    };
    const dash = apiToDashboard(dto);
    expect(dash.hasData).toBe(true);
    expect(dash.total).toBe(3);
    expect(dash.recent).toHaveLength(1);
    expect(dash.latestSummary?.periodKey).toBe('2026-kharif');
    expect(dash.latestSummary?.eventCount).toBe(3);
  });

  it('maps the season/year summary bundle', () => {
    const dto: ApiMemorySummaryBundle = {
      farm_id: 'f1',
      seasons: [
        {
          id: 's1', farm_id: 'f1', period_type: 'season', period_key: '2026-kharif',
          season: 'kharif', year: 2026, crop: 'paddy', summary: 'memory.summary.period',
          params: null, highlights: [], event_count: 2, importance: 'high',
          generated_at: '2026-08-01T00:00:00.000Z',
        },
      ],
      years: [
        {
          id: 'y1', farm_id: 'f1', period_type: 'year', period_key: '2026',
          season: null, year: 2026, crop: 'paddy', summary: 'memory.summary.period',
          params: null, highlights: [], event_count: 5, importance: 'critical',
          generated_at: '2026-08-01T00:00:00.000Z',
        },
      ],
    };
    const bundle = apiToSummaryBundle(dto);
    expect(bundle.seasons).toHaveLength(1);
    expect(bundle.years[0].periodType).toBe('year');
    expect(bundle.years[0].eventCount).toBe(5);
  });
});
