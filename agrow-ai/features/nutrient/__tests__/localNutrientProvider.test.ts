jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localNutrientProvider } from '../services/localNutrientProvider';
import { NutrientError } from '../services/nutrientProvider';
import { nutrientStorage } from '../services/nutrientStorage';
import type { AnalyzeInput } from '../types';

const FARM = 'farm-1';

function input(overrides: Partial<AnalyzeInput> = {}): AnalyzeInput {
  return {
    imageBase64: 'x',
    mimeType: 'image/jpeg',
    imageUri: 'file://leaf.jpg',
    language: 'en',
    captureMethod: 'camera',
    farmId: FARM,
    crop: 'paddy',
    ...overrides,
  };
}

describe('localNutrientProvider (offline)', () => {
  beforeEach(() => nutrientStorage.clear());

  it('analyses a leaf into a stored report — honest "possible" offline', async () => {
    const report = await localNutrientProvider.analyze(input());
    expect(report.provider).toBe('mock');
    expect(report.analysis?.primaryDeficiency).toBe('nitrogen');
    // No soil/satellite/weather references offline → never a fabricated "confirmed".
    expect(report.analysis?.status).toBe('possible');
    expect(report.analysis?.needsTest).toBe(true);
    expect(report.symptoms.length).toBeGreaterThan(0);
    expect(report.recommendations.some((r) => r.code.startsWith('nutrient.rec.'))).toBe(true);
  });

  it('lists history newest-first and exposes the latest', async () => {
    await localNutrientProvider.analyze(input());
    await localNutrientProvider.analyze(input());
    const history = await localNutrientProvider.history(FARM);
    expect(history).toHaveLength(2);
    const latest = await localNutrientProvider.latest(FARM);
    expect(latest).not.toBeNull();
    expect(latest?.id).toBe(history[0].id);
  });

  it('returns the latest report recommendations', async () => {
    await localNutrientProvider.analyze(input());
    const recs = await localNutrientProvider.recommendations(FARM);
    expect(recs.length).toBeGreaterThan(0);
  });

  it('sanitizes stored Groundnut history and recommendations', async () => {
    const created = await localNutrientProvider.analyze(input({ crop: 'Groundnut' }));
    const report = await localNutrientProvider.getReport(created.id);
    expect(report.analysis).toMatchObject({
      status: 'not_confirmed',
      confidence: null,
      confidenceBand: null,
      needsTest: true,
      needsExpert: true,
      explanationEnglish: null,
      explanationTamil: null,
    });
    expect(report.recommendations.map((rec) => rec.category)).toEqual(['test', 'expert']);
    expect((await localNutrientProvider.history(FARM))[0].analysis?.confidenceBand).toBeNull();
  });

  it('fetches a report by id and throws when missing', async () => {
    const report = await localNutrientProvider.analyze(input());
    expect((await localNutrientProvider.getReport(report.id)).id).toBe(report.id);
    await expect(localNutrientProvider.getReport('nope')).rejects.toBeInstanceOf(NutrientError);
  });

  it('returns an empty history / null latest before any analysis', async () => {
    expect(await localNutrientProvider.history(FARM)).toEqual([]);
    expect(await localNutrientProvider.latest(FARM)).toBeNull();
    expect(await localNutrientProvider.recommendations(FARM)).toEqual([]);
  });
});
