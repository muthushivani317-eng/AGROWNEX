jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localSatelliteProvider } from '../services/localSatelliteProvider';
import { satelliteStorage } from '../services/satelliteStorage';

const FARM = 'farm-1';

describe('localSatelliteProvider (offline sample provider)', () => {
  beforeEach(() => satelliteStorage.clear());

  it('produces a deterministic, clearly-flagged sample session on refresh', async () => {
    const s = await localSatelliteProvider.refresh(FARM, true);
    expect(s.status).toBe('available');
    expect(s.isSample).toBe(true); // never presented as a real scene
    expect(s.provider).toBe('mock');
    expect(s.ndvi).not.toBeNull();
    expect(s.vegetationHealth).not.toBeNull();
    expect(s.confidence).toBeLessThanOrEqual(55); // sample cap
    expect(s.indices.length).toBeGreaterThan(0);
    expect(s.images).toEqual([]); // no fabricated imagery
  });

  it('reports an honest "never refreshed" dashboard before any scan', async () => {
    const dash = await localSatelliteProvider.dashboard(FARM, true);
    expect(dash.hasData).toBe(false);
    expect(dash.status).toBe('pending');
    expect(dash.messageCode).toBe('satellite.status.never_refreshed');
    expect(dash.session).toBeNull();
  });

  it('reports an honest "no polygon" state and stores no fabricated data', async () => {
    const dashBefore = await localSatelliteProvider.dashboard(FARM, false);
    expect(dashBefore.messageCode).toBe('satellite.status.no_polygon');

    const s = await localSatelliteProvider.refresh(FARM, false);
    expect(s.status).toBe('unavailable');
    expect(s.unavailableReason).toBe('no_polygon');
    expect(s.ndvi).toBeNull();
    expect(s.alerts).toEqual([]); // no_polygon → no alerts

    const dash = await localSatelliteProvider.dashboard(FARM, false);
    expect(dash.hasData).toBe(false);
    expect(dash.messageCode).toBe('satellite.status.no_polygon');
  });

  it('surfaces the latest available session in the dashboard', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    const dash = await localSatelliteProvider.dashboard(FARM, true);
    expect(dash.hasData).toBe(true);
    expect(dash.status).toBe('available');
    expect(dash.messageCode).toBeNull();
    expect(dash.session).not.toBeNull();
  });

  it('lists history newest-first for available sessions only', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    await localSatelliteProvider.refresh(FARM, true);
    await localSatelliteProvider.refresh(FARM, false); // unavailable — excluded
    const page = await localSatelliteProvider.history(FARM);
    expect(page.total).toBe(2);
    expect(page.items).toHaveLength(2);
    // Newest first: the second scan was recorded most recently.
    expect(new Date(page.items[0].recordedAt).getTime()).toBeGreaterThanOrEqual(
      new Date(page.items[1].recordedAt).getTime(),
    );
  });

  it('aggregates a timeline over available sessions', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    await localSatelliteProvider.refresh(FARM, true);
    const timeline = await localSatelliteProvider.timeline(FARM, 'weekly');
    expect(timeline.range).toBe('weekly');
    expect(timeline.points.length).toBeGreaterThan(0);
    const total = timeline.points.reduce((sum, p) => sum + p.count, 0);
    expect(total).toBe(2);
  });

  it('returns the latest session alerts (empty when the farm is healthy)', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    const alerts = await localSatelliteProvider.alerts(FARM);
    expect(Array.isArray(alerts)).toBe(true);
    expect(alerts.every((a) => a.code.startsWith('satellite.alert.'))).toBe(true);
  });

  it('returns no alerts for a farm that was never scanned', async () => {
    expect(await localSatelliteProvider.alerts(FARM)).toEqual([]);
  });
});
