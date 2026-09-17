jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `entry-${++n}` };
});

import type { Farm } from '../types';
import { farmOutbox, resolveFarmConflict } from '../services/farmSync';

function farm(id: string, updatedAt: string): Farm {
  return {
    id,
    name: id,
    crop: null,
    cropVariety: null,
    sowingDate: null,
    soilType: null,
    irrigationType: null,
    waterSource: null,
    areaHectares: null,
    areaSource: 'auto',
    notes: null,
    status: 'active',
    location: null,
    boundary: null,
    images: [],
    imageCount: 0,
    createdAt: updatedAt,
    updatedAt,
    syncStatus: 'pending',
  };
}

describe('resolveFarmConflict', () => {
  it('keeps the newer local edit', () => {
    const local = farm('a', '2026-07-02T00:00:00Z');
    const remote = farm('a', '2026-07-01T00:00:00Z');
    const merged = resolveFarmConflict(local, remote);
    expect(merged.updatedAt).toBe(local.updatedAt);
    expect(merged.syncStatus).toBe('synced');
  });

  it('prefers the server when it is newer or tied', () => {
    const local = farm('a', '2026-07-01T00:00:00Z');
    const remote = farm('a', '2026-07-02T00:00:00Z');
    expect(resolveFarmConflict(local, remote).updatedAt).toBe(remote.updatedAt);

    const tieLocal = farm('a', '2026-07-01T00:00:00Z');
    const tieRemote = farm('a', '2026-07-01T00:00:00Z');
    expect(resolveFarmConflict(tieLocal, tieRemote).syncStatus).toBe('synced');
  });
});

describe('farmOutbox', () => {
  beforeEach(() => farmOutbox.clear());

  it('enqueues, lists and removes entries', () => {
    farmOutbox.enqueue({ op: 'create', farmId: 'f1' });
    farmOutbox.enqueue({ op: 'delete', farmId: 'f2' });
    expect(farmOutbox.count()).toBe(2);

    const entries = farmOutbox.all();
    expect(entries.map((e) => e.op)).toEqual(['create', 'delete']);

    farmOutbox.remove(entries[0].entryId);
    expect(farmOutbox.count()).toBe(1);
    expect(farmOutbox.all()[0].op).toBe('delete');
  });
});
