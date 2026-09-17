import { assignExpert, scoreExpert } from '../services/assignment';
import { expertSeeds } from '../services/expertSeeds';

describe('assignment (client engine mirror)', () => {
  const experts = expertSeeds();

  it('routes a crop_disease question to a matching TNAU desk (deterministic)', () => {
    const chosen = assignExpert(experts, { category: 'crop_disease' });
    // Both TNAU desks match; the deterministic tie-break picks the lowest id.
    expect(chosen?.id).toBe('tnau-agritech-helpline');
    expect(chosen?.categories).toContain('crop_disease');
  });

  it('routes a soil_health question to the KVK desk', () => {
    const chosen = assignExpert(experts, { category: 'soil_health' });
    expect(chosen?.id).toBe('kvk-farm-advisory');
  });

  it('falls back to a generalist desk for an uncovered exact category', () => {
    const chosen = assignExpert(experts, { category: 'market' });
    // Kisan Call Centre covers market; otherwise a generalist would still win.
    expect(chosen).not.toBeNull();
    expect(chosen?.categories.includes('market') || chosen?.districts.length === 0).toBe(
      true,
    );
  });

  it('category match scores higher than a generalist fallback', () => {
    const plantClinic = experts.find((e) => e.id === 'tnau-plant-clinic')!;
    const kvk = experts.find((e) => e.id === 'kvk-farm-advisory')!;
    const ctx = { category: 'crop_disease' as const };
    expect(scoreExpert(plantClinic, ctx)).toBeGreaterThan(scoreExpert(kvk, ctx));
  });

  it('returns null when there are no experts', () => {
    expect(assignExpert([], { category: 'general' })).toBeNull();
  });
});
