import { apiToOrganicPractice, apiToOrganicProfile, practiceInputToApi, profileInputToApi } from '../services/organicMapper';

describe('organic API boundary mapper', () => {
  it('maps the farm profile without treating farming mode as certification', () => {
    const profile = apiToOrganicProfile({ farm_id: 'farm-1', mode: 'fully_organic', updated_at: '2026-09-09T00:00:00Z' });
    expect(profile).toMatchObject({ farmId: 'farm-1', mode: 'fully_organic', certificationStatus: 'not_claimed', syncStatus: 'synced' });
    expect(profileInputToApi({ mode: 'transitioning', transitionStartDate: '2026-09-01', goals: ['soil'], preferredPractices: ['mulching'] })).toEqual({ mode: 'transitioning', transition_start_date: '2026-09-01', goals: ['soil'], preferred_practices: ['mulching'] });
  });

  it('maps logbook records and preserves the idempotency key', () => {
    const input = { farmId: 'farm-1', type: 'mulching' as const, title: 'Mulched plot', occurredAt: '2026-09-09T00:00:00Z', clientRequestId: 'request-1' };
    expect(practiceInputToApi(input)).toMatchObject({ farm_id: 'farm-1', practice_type: 'mulching', practice_code: 'mulching', input_reference: 'Mulched plot', occurred_at: input.occurredAt, idempotency_key: 'request-1' });
    expect(apiToOrganicPractice({ id: 'p1', farm_id: 'farm-1', practice_type: 'mulching', practice_code: 'mulching', input_reference: 'Mulched plot', occurred_at: input.occurredAt, created_at: input.occurredAt })).toMatchObject({ id: 'p1', farmId: 'farm-1', type: 'mulching', syncStatus: 'synced' });
  });
});
