import {
  contextFromQuery,
  deriveFarmerCategory,
  evaluate,
  isEligible,
  rank,
  type FarmerContext,
  type SchemeRules,
} from '../services/eligibility';
import type { Eligibility } from '../types';

const openRules = (overrides: Partial<SchemeRules> = {}): SchemeRules => ({
  states: ['all'],
  districts: ['all'],
  crops: ['all'],
  farmerCategories: ['all'],
  minLandHectares: null,
  maxLandHectares: null,
  maxAnnualIncome: null,
  status: 'active',
  ...overrides,
});

const emptyContext: FarmerContext = {
  state: null,
  district: null,
  crop: null,
  landHectares: null,
  annualIncome: null,
  farmerCategory: null,
};

describe('deriveFarmerCategory', () => {
  it('classifies holdings by size (matches the backend bands)', () => {
    expect(deriveFarmerCategory(0.5)).toBe('marginal');
    expect(deriveFarmerCategory(1)).toBe('small');
    expect(deriveFarmerCategory(1.9)).toBe('small');
    expect(deriveFarmerCategory(2)).toBe('semi_medium');
    expect(deriveFarmerCategory(4)).toBe('medium');
    expect(deriveFarmerCategory(9.9)).toBe('medium');
    expect(deriveFarmerCategory(10)).toBe('large');
    expect(deriveFarmerCategory(25)).toBe('large');
  });

  it('returns null for unknown / non-positive land', () => {
    expect(deriveFarmerCategory(null)).toBeNull();
    expect(deriveFarmerCategory(0)).toBeNull();
    expect(deriveFarmerCategory(-2)).toBeNull();
  });
});

describe('contextFromQuery', () => {
  it('defaults the state to Tamil Nadu and derives the category from land', () => {
    const ctx = contextFromQuery({ landHectares: 1.5 });
    expect(ctx.state).toBe('Tamil Nadu');
    expect(ctx.farmerCategory).toBe('small');
  });

  it('respects an explicit farmer category override', () => {
    const ctx = contextFromQuery({ landHectares: 1.5, farmerCategory: 'medium' });
    expect(ctx.farmerCategory).toBe('medium');
  });
});

describe('evaluate', () => {
  it('marks an open scheme eligible with any context', () => {
    const result = evaluate(openRules(), emptyContext);
    expect(result.status).toBe('eligible');
    expect(result.unmet).toEqual([]);
    expect(result.score).toBeGreaterThanOrEqual(10);
  });

  it('matches a list constraint case-insensitively', () => {
    const result = evaluate(openRules({ crops: ['Paddy'] }), {
      ...emptyContext,
      crop: '  paddy ',
    });
    expect(result.matched).toContain('crop');
    expect(result.status).toBe('eligible');
  });

  it('fails a violated list constraint', () => {
    const result = evaluate(openRules({ states: ['Kerala'] }), {
      ...emptyContext,
      state: 'Tamil Nadu',
    });
    expect(result.status).toBe('not_eligible');
    expect(result.score).toBe(0);
    expect(result.unmet).toContain('state');
  });

  it('is likely-eligible when a constrained value is unknown', () => {
    const result = evaluate(openRules({ crops: ['paddy'] }), emptyContext);
    expect(result.status).toBe('likely_eligible');
    expect(result.unknown).toContain('crop');
    expect(isEligible(result)).toBe(true);
  });

  it('enforces land bounds', () => {
    expect(
      evaluate(openRules({ maxLandHectares: 4 }), { ...emptyContext, landHectares: 5 })
        .status,
    ).toBe('not_eligible');
    expect(
      evaluate(openRules({ minLandHectares: 2 }), { ...emptyContext, landHectares: 1 })
        .status,
    ).toBe('not_eligible');
    expect(
      evaluate(openRules({ minLandHectares: 1, maxLandHectares: 4 }), {
        ...emptyContext,
        landHectares: 2,
      }).matched,
    ).toContain('land');
  });

  it('enforces the income ceiling', () => {
    expect(
      evaluate(openRules({ maxAnnualIncome: 200000 }), {
        ...emptyContext,
        annualIncome: 300000,
      }).status,
    ).toBe('not_eligible');
    expect(
      evaluate(openRules({ maxAnnualIncome: 200000 }), {
        ...emptyContext,
        annualIncome: 200000,
      }).matched,
    ).toContain('income');
  });

  it('never marks a closed scheme eligible', () => {
    const result = evaluate(openRules({ status: 'closed' }), emptyContext);
    expect(result.status).toBe('not_eligible');
    expect(isEligible(result)).toBe(false);
  });

  it('never marks a scheme eligible after its application deadline has passed', () => {
    const result = evaluate(
      openRules({ lastDate: '2026-07-31' }),
      emptyContext,
      new Date('2026-08-15'),
    );
    expect(result.status).toBe('not_eligible');
    expect(result.unmet).toContain('deadline');
  });

  it('still marks a scheme eligible before its deadline, or when today is not supplied', () => {
    expect(
      evaluate(openRules({ lastDate: '2026-12-31' }), emptyContext, new Date('2026-08-15'))
        .status,
    ).toBe('eligible');
    expect(evaluate(openRules({ lastDate: '2026-07-31' }), emptyContext).status).toBe(
      'eligible',
    );
  });

  it('scores targeted matches above a generic open scheme', () => {
    const ctx = { ...emptyContext, state: 'Tamil Nadu', crop: 'paddy' };
    const targeted = evaluate(
      openRules({ states: ['Tamil Nadu'], crops: ['paddy'] }),
      ctx,
    );
    const generic = evaluate(openRules(), ctx);
    expect(targeted.score).toBeGreaterThan(generic.score);
  });
});

describe('rank', () => {
  const withResult = (
    lastDate: string | null,
    status: Eligibility['status'],
    score: number,
  ) => ({
    lastDate,
    eligibility: { status, score, matched: [], unmet: [], unknown: [] } as Eligibility,
  });

  it('orders eligible before likely-eligible', () => {
    const ordered = rank([
      withResult(null, 'likely_eligible', 90),
      withResult(null, 'eligible', 70),
    ]);
    expect(ordered[0].eligibility.status).toBe('eligible');
  });

  it('orders by score within a status, then soonest deadline', () => {
    const ordered = rank([
      withResult(null, 'eligible', 80),
      withResult('2026-12-31', 'eligible', 80),
      withResult('2026-07-20', 'eligible', 80),
      withResult(null, 'eligible', 95),
    ]);
    expect(ordered[0].eligibility.score).toBe(95);
    expect(ordered[1].lastDate).toBe('2026-07-20');
    expect(ordered[2].lastDate).toBe('2026-12-31');
    expect(ordered[3].lastDate).toBeNull();
  });
});
