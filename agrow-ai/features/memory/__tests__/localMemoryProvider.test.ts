jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `mem-${++n}` };
});

import { localSatelliteProvider } from '@/features/satellite/services/localSatelliteProvider';
import { satelliteStorage } from '@/features/satellite/services/satelliteStorage';
import { nutrientStorage } from '@/features/nutrient/services/nutrientStorage';

import { MemoryError } from '../services/memoryProvider';
import { localMemoryProvider } from '../services/localMemoryProvider';
import { memoryStorage } from '../services/memoryStorage';

const FARM = 'farm-1';

describe('localMemoryProvider (offline aggregation)', () => {
  beforeEach(() => {
    memoryStorage.clear();
    satelliteStorage.clear();
    nutrientStorage.clear();
  });

  it('rebuilds an honest empty memory when no module data exists', async () => {
    const result = await localMemoryProvider.rebuild(FARM);
    expect(result.created).toBe(0);
    expect(result.total).toBe(0);

    const dash = await localMemoryProvider.dashboard(FARM);
    expect(dash.hasData).toBe(false);
    expect(dash.messageCode).toBe('memory.status.no_memory');
    expect(dash.recent).toEqual([]);
  });

  it('learns from a sibling satellite session (guarded cross-module read)', async () => {
    // Seed a real available satellite session in its own local store.
    await localSatelliteProvider.refresh(FARM, true);

    const result = await localMemoryProvider.rebuild(FARM);
    expect(result.created).toBeGreaterThan(0);

    const dash = await localMemoryProvider.dashboard(FARM);
    expect(dash.hasData).toBe(true);
    expect(dash.recent[0].sourceModule).toBe('satellite');
    // A locally-derived memory is clearly flagged, never mistaken for verified.
    expect(dash.recent[0].isSample).toBe(true);
  });

  it('throws until a memory exists, then returns the latest', async () => {
    await expect(localMemoryProvider.latest(FARM)).rejects.toBeInstanceOf(MemoryError);
    await localSatelliteProvider.refresh(FARM, true);
    await localMemoryProvider.rebuild(FARM);
    const latest = await localMemoryProvider.latest(FARM);
    expect(latest.sourceModule).toBe('satellite');
  });

  it('filters the timeline by source module', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    await localMemoryProvider.rebuild(FARM);

    const all = await localMemoryProvider.history(FARM);
    expect(all.total).toBeGreaterThan(0);

    const none = await localMemoryProvider.history(FARM, { sourceModule: 'disease' });
    expect(none.total).toBe(0);

    const sat = await localMemoryProvider.history(FARM, { sourceModule: 'satellite' });
    expect(sat.total).toBe(all.total);
  });

  it('fetches a memory by id and rejects an unknown id', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    await localMemoryProvider.rebuild(FARM);
    const latest = await localMemoryProvider.latest(FARM);
    const fetched = await localMemoryProvider.getMemory(latest.id);
    expect(fetched.id).toBe(latest.id);
    await expect(localMemoryProvider.getMemory('nope')).rejects.toBeInstanceOf(MemoryError);
  });

  it('exposes season/year summaries derived from the memories', async () => {
    await localSatelliteProvider.refresh(FARM, true);
    await localMemoryProvider.rebuild(FARM);
    const bundle = await localMemoryProvider.summary(FARM);
    expect(bundle.seasons.length + bundle.years.length).toBeGreaterThan(0);
  });
});
