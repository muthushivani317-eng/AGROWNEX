import { localSchemeProvider } from '../services/localSchemeProvider';
import { SchemeError } from '../services/schemeProvider';
import { schemeStorage } from '../services/schemeStorage';
import type { SchemeQuery } from '../types';

const marginalPulseFarmer: SchemeQuery = {
  state: 'Tamil Nadu',
  district: 'Thanjavur',
  crop: 'black gram',
  landHectares: 1.5,
  annualIncome: 150000,
};

describe('localSchemeProvider', () => {
  beforeEach(() => schemeStorage.clear());

  it('lists verified sample schemes, filterable by category', async () => {
    const all = await localSchemeProvider.list({});
    expect(all.total).toBeGreaterThan(3);

    const insurance = await localSchemeProvider.list({ category: 'insurance' });
    expect(insurance.items.every((s) => s.category === 'insurance')).toBe(true);
    expect(insurance.total).toBeGreaterThanOrEqual(1);
  });

  it('lists schemes matching a search term', async () => {
    const result = await localSchemeProvider.list({ search: 'kisan' });
    expect(result.items.some((s) => s.title.toLowerCase().includes('kisan'))).toBe(true);
  });

  it('returns eligible schemes ranked, including targeted ones', async () => {
    const { results, context } = await localSchemeProvider.eligible(
      marginalPulseFarmer,
    );
    const slugs = results.items.map((s) => s.slug);
    expect(slugs).toContain('pm-kisan'); // open central scheme
    expect(slugs).toContain('tn-farmers-security-scheme'); // TN + small/marginal targeted
    expect(context.farmerCategory).toBe('small');

    const scores = results.items.map((s) => s.eligibility?.score ?? 0);
    expect(scores).toEqual([...scores].sort((a, b) => b - a));
  });

  it('excludes schemes whose hard constraints fail', async () => {
    const { results } = await localSchemeProvider.eligible({
      state: 'Tamil Nadu',
      crop: 'wheat',
      landHectares: 20,
      annualIncome: 900000,
    });
    const slugs = results.items.map((s) => s.slug);
    expect(slugs).not.toContain('tn-drip-subsidy'); // needs <= 5 ha
    expect(slugs).not.toContain('tn-farmers-security-scheme'); // needs marginal/small (20ha -> large)
    expect(slugs).toContain('pm-kisan');
  });

  it('excludes state-specific schemes for another state', async () => {
    const { results } = await localSchemeProvider.eligible({ state: 'Kerala' });
    const slugs = results.items.map((s) => s.slug);
    expect(slugs).not.toContain('tn-drip-subsidy');
    expect(slugs).not.toContain('tn-farm-mechanization');
    expect(slugs).not.toContain('tn-farmers-security-scheme');
    expect(slugs).toContain('pm-kisan');
  });

  it('recommends at least the minimum set', async () => {
    const { items } = await localSchemeProvider.recommended({ state: 'Tamil Nadu' });
    expect(items.length).toBeGreaterThanOrEqual(3);
    expect(
      items.every((s) => s.eligibility && s.eligibility.status !== 'not_eligible'),
    ).toBe(true);
  });

  it('returns full detail with documents, steps and eligibility', async () => {
    const detail = await localSchemeProvider.detail('local-pmfby', {
      state: 'Tamil Nadu',
    });
    expect(detail.slug).toBe('pmfby');
    expect(detail.documents.length).toBeGreaterThan(0);
    expect(detail.applicationSteps.length).toBeGreaterThan(0);
    expect(detail.eligibility).not.toBeNull();
    expect(detail.verifiedAt).not.toBeNull();
  });

  it('throws for an unknown scheme', async () => {
    await expect(localSchemeProvider.detail('nope', {})).rejects.toBeInstanceOf(
      SchemeError,
    );
  });

  it('adds, lists and removes bookmarks; blocks duplicates', async () => {
    await localSchemeProvider.addBookmark('local-kcc');
    let bookmarks = await localSchemeProvider.bookmarks({ state: 'Tamil Nadu' });
    expect(bookmarks.map((b) => b.slug)).toContain('kcc');
    expect(bookmarks[0].bookmarked).toBe(true);
    expect(bookmarks[0].eligibility).not.toBeNull();

    await expect(localSchemeProvider.addBookmark('local-kcc')).rejects.toBeInstanceOf(
      SchemeError,
    );

    await localSchemeProvider.removeBookmark('local-kcc');
    bookmarks = await localSchemeProvider.bookmarks({});
    expect(bookmarks).toHaveLength(0);
  });

  it('reflects the bookmarked flag in eligible listings', async () => {
    await localSchemeProvider.addBookmark('local-pm-kisan');
    const { results } = await localSchemeProvider.eligible({ state: 'Tamil Nadu' });
    const pmKisan = results.items.find((s) => s.slug === 'pm-kisan');
    expect(pmKisan?.bookmarked).toBe(true);
  });
});
