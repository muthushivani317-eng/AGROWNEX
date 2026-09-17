import { resolveOrganicFeatureEnabled } from '../featureFlag';
describe('organic feature flag', () => {
  it('is available by default and fails closed when explicitly disabled', () => { expect(resolveOrganicFeatureEnabled(undefined)).toBe(true); expect(resolveOrganicFeatureEnabled('true')).toBe(true); expect(resolveOrganicFeatureEnabled('false')).toBe(false); });
});
