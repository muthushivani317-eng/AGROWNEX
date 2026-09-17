// Deterministic, unique ids (the global expo-crypto mock returns a fixed UUID).
jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `farm-${++n}` };
});

import type { FarmInput, GeoJSONPolygon } from '../types';
import { localFarmProvider } from '../services/localFarmProvider';
import { farmStorage } from '../services/farmStorage';

const square: GeoJSONPolygon = {
  type: 'Polygon',
  coordinates: [
    [
      [78.1, 9.9],
      [78.11, 9.9],
      [78.11, 9.91],
      [78.1, 9.91],
      [78.1, 9.9],
    ],
  ],
};

function input(overrides: Partial<FarmInput> = {}): FarmInput {
  return {
    name: 'Field',
    crop: 'paddy',
    cropVariety: null,
    sowingDate: null,
    soilType: null,
    irrigationType: null,
    waterSource: null,
    notes: null,
    status: 'active',
    areaHectares: null,
    areaSource: 'auto',
    location: null,
    boundary: null,
    ...overrides,
  };
}

describe('localFarmProvider', () => {
  beforeEach(() => farmStorage.clear());

  it('creates and reads a farm', async () => {
    const farm = await localFarmProvider.create(input({ name: 'North Field' }));
    expect(farm.name).toBe('North Field');
    const got = await localFarmProvider.get(farm.id);
    expect(got.id).toBe(farm.id);
  });

  it('rejects a duplicate name (case/space-insensitive)', async () => {
    await localFarmProvider.create(input({ name: 'Paddy Plot' }));
    await expect(
      localFarmProvider.create(input({ name: '  paddy plot ' })),
    ).rejects.toThrow();
  });

  it('supports multiple farms and status filtering', async () => {
    await localFarmProvider.create(input({ name: 'A', status: 'active' }));
    await localFarmProvider.create(input({ name: 'B', status: 'draft' }));

    const all = await localFarmProvider.list({});
    expect(all.total).toBe(2);

    const drafts = await localFarmProvider.list({ status: 'draft' });
    expect(drafts.total).toBe(1);
    expect(drafts.items[0].name).toBe('B');
  });

  it('computes area from a boundary on create', async () => {
    const farm = await localFarmProvider.create(
      input({ name: 'Bounded', boundary: { geojson: square, source: 'drawn' } }),
    );
    expect(farm.boundary?.vertexCount).toBe(4);
    expect(farm.areaHectares).toBeGreaterThan(0);
    expect(farm.areaHectares).toBeCloseTo(farm.boundary?.areaHectares ?? -1);
  });

  it('honours a manual area override', async () => {
    const farm = await localFarmProvider.create(
      input({
        name: 'Manual',
        areaSource: 'manual',
        areaHectares: 2.5,
        boundary: { geojson: square, source: 'drawn' },
      }),
    );
    expect(farm.areaHectares).toBe(2.5);
    expect(farm.boundary?.areaHectares).not.toBe(2.5);
  });

  it('updates a farm in place', async () => {
    const farm = await localFarmProvider.create(input({ name: 'Old' }));
    const updated = await localFarmProvider.update(
      farm.id,
      input({ name: 'New', crop: 'cotton' }),
    );
    expect(updated.id).toBe(farm.id);
    expect(updated.name).toBe('New');
    expect(updated.crop).toBe('cotton');
  });

  it('soft context: delete removes the farm', async () => {
    const farm = await localFarmProvider.create(input({ name: 'Temp' }));
    await localFarmProvider.remove(farm.id);
    await expect(localFarmProvider.get(farm.id)).rejects.toThrow();
  });

  it('updates a boundary and syncs the auto area', async () => {
    const farm = await localFarmProvider.create(input({ name: 'Drawable' }));
    const boundary = await localFarmProvider.updateBoundary(farm.id, {
      geojson: square,
      source: 'drawn',
    });
    expect(boundary.areaHectares).toBeGreaterThan(0);
    const got = await localFarmProvider.get(farm.id);
    expect(got.areaHectares).toBeCloseTo(boundary.areaHectares ?? -1);
  });

  it('adds and lists images', async () => {
    const farm = await localFarmProvider.create(input({ name: 'Photos' }));
    await localFarmProvider.addImage(farm.id, { fileUrl: 'https://cdn/a.jpg' });
    const images = await localFarmProvider.listImages(farm.id);
    expect(images).toHaveLength(1);
    expect(images[0].fileUrl).toBe('https://cdn/a.jpg');
  });
});
