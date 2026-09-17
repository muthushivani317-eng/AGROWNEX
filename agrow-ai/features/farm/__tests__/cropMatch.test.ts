import { matchCropId } from '../utils/cropMatch';

describe('matchCropId', () => {
  it('matches direct crop names and ids', () => {
    expect(matchCropId('Banana')).toBe('banana');
    expect(matchCropId('cotton')).toBe('cotton');
  });

  it('matches known crop aliases', () => {
    expect(matchCropId('rice')).toBe('paddy');
    expect(matchCropId('peanut')).toBe('groundnut');
  });

  it('is case-insensitive', () => {
    expect(matchCropId('SuGaRcAnE')).toBe('sugarcane');
  });

  it('returns null when no crop matches', () => {
    expect(matchCropId('rose')).toBeNull();
  });

  it('returns null for empty or null input', () => {
    expect(matchCropId('')).toBeNull();
    expect(matchCropId(null)).toBeNull();
  });
});
