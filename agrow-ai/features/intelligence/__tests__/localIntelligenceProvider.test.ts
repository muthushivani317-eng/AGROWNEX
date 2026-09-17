jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `intel-${++n}` };
});

import { localSatelliteProvider } from '@/features/satellite/services/localSatelliteProvider';
import { satelliteStorage } from '@/features/satellite/services/satelliteStorage';
import { nutrientStorage } from '@/features/nutrient/services/nutrientStorage';

import { IntelligenceError } from '../services/intelligenceProvider';
import { intelligenceStorage } from '../services/intelligenceStorage';
import { localIntelligenceProvider } from '../services/localIntelligenceProvider';

const FARM = 'farm-1';

describe('localIntelligenceProvider (offline aggregation)', () => {
  beforeEach(() => {
    intelligenceStorage.clear();
    satelliteStorage.clear();
    nutrientStorage.clear();
  });

  it('produces an honest empty report when no module data exists', async () => {
    const report = await localIntelligenceProvider.refresh(FARM);
    // Nothing to aggregate → never fabricated: no overall score, zero confidence.
    expect(report.overallHealthScore).toBeNull();
    expect(report.confidence).toBe(0);
    expect(report.overallRisk).toBe('low');
    expect(report.sourcesUsed).toEqual([]);
    expect(report.isSample).toBe(true); // a locally-derived assessment, clearly flagged
  });

  it('preserves a lone satellite module without fabricating an overall score', async () => {
    // Seed a real available satellite session in its own local store.
    await localSatelliteProvider.refresh(FARM, true);

    const report = await localIntelligenceProvider.refresh(FARM);
    expect(report.sourcesUsed).toContain('satellite');
    expect(report.health?.satelliteScore).not.toBeNull();
    expect(report.overallHealthScore).toBeNull();
    expect(report.confidence).toBeGreaterThan(0);
  });

  it('reports an honest empty dashboard before any refresh', async () => {
    const dash = await localIntelligenceProvider.dashboard(FARM);
    expect(dash.hasData).toBe(false);
    expect(dash.messageCode).toBe('intelligence.status.no_report');
    expect(dash.report).toBeNull();
  });

  it('surfaces the latest report in the dashboard', async () => {
    await localIntelligenceProvider.refresh(FARM);
    const dash = await localIntelligenceProvider.dashboard(FARM);
    expect(dash.hasData).toBe(true);
    expect(dash.report).not.toBeNull();
  });

  it('throws until a report exists, then returns the latest', async () => {
    await expect(localIntelligenceProvider.latest(FARM)).rejects.toBeInstanceOf(IntelligenceError);
    const created = await localIntelligenceProvider.refresh(FARM);
    const latest = await localIntelligenceProvider.latest(FARM);
    expect(latest.id).toBe(created.id);
  });

  it('lists history newest-first and fetches a report by id', async () => {
    const first = await localIntelligenceProvider.refresh(FARM);
    const second = await localIntelligenceProvider.refresh(FARM);
    const page = await localIntelligenceProvider.history(FARM);
    expect(page.total).toBe(2);
    expect(page.items[0].reportId).toBe(second.id);

    const fetched = await localIntelligenceProvider.getReport(first.id);
    expect(fetched.id).toBe(first.id);
    await expect(localIntelligenceProvider.getReport('nope')).rejects.toBeInstanceOf(
      IntelligenceError,
    );
  });
});
