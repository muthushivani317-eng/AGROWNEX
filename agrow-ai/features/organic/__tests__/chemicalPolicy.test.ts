import { applyChemicalPolicy, chemicalPolicyForMode } from '../chemicalPolicy';

jest.mock('../hooks/useOrganic', () => ({ useOrganicProfile: jest.fn() }));

const t = (key: string) => key;

describe('chemicalPolicyForMode', () => {
  it('maps each farming mode', () => {
    expect(chemicalPolicyForMode('conventional')).toBe('show');
    expect(chemicalPolicyForMode(undefined)).toBe('show');
    expect(chemicalPolicyForMode('organic_preferred')).toBe('last_resort');
    expect(chemicalPolicyForMode('transitioning')).toBe('hide');
    expect(chemicalPolicyForMode('fully_organic')).toBe('hide');
  });
});

describe('applyChemicalPolicy', () => {
  it('hides chemicals for organic farms', () => {
    expect(applyChemicalPolicy(['Fungicide'], 'hide', t)).toEqual(['organic.chemicalNotAllowed']);
  });
  it('flags chemicals as last resort', () => {
    expect(applyChemicalPolicy(['Fungicide'], 'last_resort', t)).toEqual(['Fungicide', 'organic.chemicalLastResort']);
  });
  it('leaves conventional and empty lists unchanged', () => {
    expect(applyChemicalPolicy(['Fungicide'], 'show', t)).toEqual(['Fungicide']);
    expect(applyChemicalPolicy([], 'hide', t)).toEqual([]);
  });
});
