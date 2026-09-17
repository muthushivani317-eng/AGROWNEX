import { apiToOrganicPlanBundle } from '../services/organicPlanMapper';
describe('organic plan mapper safety', () => {
  it('forces every satellite action to scouting-only', () => {
    const result = apiToOrganicPlanBundle({ farm_id: 'f1', generated_at: '2026-09-09T00:00:00Z', actions: [{ id: 'a1', action_type: 'satellite', title: 'Inspect low-vigor zone', description: 'Check the field', priority: 1, state: 'ready', source_organization: 'TNAU', source_reference: 'ref', review_status: 'verified', source_action_id: 'source-1', scouting_only: false }] });
    expect(result.actions[0]).toMatchObject({ kind: 'satellite', scoutingOnly: true });
  });
});
