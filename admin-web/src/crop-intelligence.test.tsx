import { describe, expect, it } from 'vitest';
import { completeness, cropCoverage, type CropIntelligenceData } from './CropIntelligence';
describe('crop intelligence evidence', () => {
  it('distinguishes unavailable, empty and partially recorded data', () => {
    expect(completeness(undefined, undefined)).toBe('Unavailable');
    expect(completeness(0, 0)).toBe('No farms');
    expect(completeness(0, 3)).toBe('Missing');
    expect(completeness(1, 3)).toBe('1 of 3 farms');
    expect(completeness(3, 3)).toBe('Complete');
  });
  it('combines casing variants without inflating crop variety count', () => {
    const data = { summary: { farm_count: 3 }, by_crop: [{ label: 'Paddy', farm_count: 1 }, { label: 'paddy', farm_count: 2 }] } as CropIntelligenceData;
    expect(cropCoverage(data)).toEqual([{ label: 'Paddy', count: 3, percent: 100 }]);
  });
  it('does not divide by zero for empty coverage', () => {
    const data = { summary: { farm_count: 0 }, by_crop: [{ label: 'Paddy', farm_count: 0 }] } as CropIntelligenceData;
    expect(cropCoverage(data)[0].percent).toBe(0);
  });
});
