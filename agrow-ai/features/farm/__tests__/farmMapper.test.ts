import type { ApiFarm, BoundaryInput, FarmInput, GeoJSONPolygon } from '../types';
import {
  apiToFarm,
  assembleFarm,
  computeBoundary,
  farmInputToApi,
  resolveArea,
} from '../services/farmMapper';

const squarePolygon: GeoJSONPolygon = {
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

const baseInput: FarmInput = {
  name: 'North Field',
  crop: 'paddy',
  cropVariety: 'ADT 43',
  sowingDate: '2026-06-01',
  soilType: 'alluvial',
  irrigationType: 'canal',
  waterSource: 'river',
  notes: 'near the well',
  status: 'active',
  areaHectares: null,
  areaSource: 'auto',
  location: {
    latitude: 9.9,
    longitude: 78.1,
    accuracy: 5,
    elevation: null,
    address: null,
    district: 'madurai',
    block: 'Melur',
    village: null,
    source: 'gps',
  },
  boundary: { geojson: squarePolygon, source: 'drawn' },
};

describe('farmMapper', () => {
  it('maps an API farm to the domain model', () => {
    const dto: ApiFarm = {
      id: 'f1',
      user_id: 'u1',
      name: 'Riverside',
      crop: 'cotton',
      crop_variety: null,
      sowing_date: '2026-05-01',
      soil_type: 'black',
      irrigation_type: 'drip',
      water_source: 'borewell',
      area_hectares: 1.24,
      area_source: 'auto',
      notes: null,
      status: 'active',
      created_at: '2026-07-01T00:00:00Z',
      updated_at: '2026-07-02T00:00:00Z',
      location: null,
      boundary: null,
      images: [],
      image_count: 0,
    };
    const farm = apiToFarm(dto);
    expect(farm.name).toBe('Riverside');
    expect(farm.cropVariety).toBeNull();
    expect(farm.areaHectares).toBe(1.24);
    expect(farm.syncStatus).toBe('synced');
  });

  it('builds a snake_case payload, omitting null area and empty sub-objects', () => {
    const payload = farmInputToApi({ ...baseInput, areaHectares: null });
    expect(payload.area_hectares).toBeUndefined();
    expect(payload.crop_variety).toBe('ADT 43');
    expect(payload.boundary).toEqual({ geojson: squarePolygon, source: 'drawn' });
    expect(payload.location).toMatchObject({ district: 'madurai', source: 'gps' });

    const noExtras = farmInputToApi({
      ...baseInput,
      location: null,
      boundary: null,
      areaHectares: 2,
    });
    expect(noExtras.location).toBeUndefined();
    expect(noExtras.boundary).toBeUndefined();
    expect(noExtras.area_hectares).toBe(2);
  });

  it('computes boundary metrics from a polygon', () => {
    const boundary = computeBoundary({ geojson: squarePolygon, source: 'drawn' });
    expect(boundary.vertexCount).toBe(4);
    expect(boundary.areaHectares).toBeGreaterThan(0);
    expect(boundary.perimeterM).toBeGreaterThan(0);
    expect(boundary.centroidLat).toBeCloseTo(9.905, 3);
  });

  it('resolves effective area (manual override wins)', () => {
    const boundary = computeBoundary({ geojson: squarePolygon, source: 'drawn' });
    expect(resolveArea('auto', null, boundary)).toBe(boundary.areaHectares);
    expect(resolveArea('manual', 3.5, boundary)).toBe(3.5);
    expect(resolveArea('manual', null, boundary)).toBe(boundary.areaHectares);
    expect(resolveArea('auto', 2, null)).toBe(2);
  });

  it('assembles a farm, preserving existing images and creation time', () => {
    const created = assembleFarm(baseInput, { id: 'x1' });
    expect(created.id).toBe('x1');
    expect(created.boundary?.vertexCount).toBe(4);
    expect(created.areaHectares).toBe(created.boundary?.areaHectares);
    expect(created.syncStatus).toBe('synced');

    const existing = {
      ...created,
      images: [
        {
          id: 'img1',
          fileUrl: 'x',
          fileName: null,
          mimeType: null,
          fileSize: null,
          caption: null,
          createdAt: null,
        },
      ],
      createdAt: '2020-01-01T00:00:00Z',
    };
    const updated = assembleFarm(
      { ...baseInput, name: 'Renamed' },
      { id: 'x1', existing, syncStatus: 'pending' },
    );
    expect(updated.name).toBe('Renamed');
    expect(updated.images).toHaveLength(1);
    expect(updated.createdAt).toBe('2020-01-01T00:00:00Z');
    expect(updated.syncStatus).toBe('pending');
  });
});
