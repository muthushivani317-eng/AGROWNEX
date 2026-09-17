import { buildOrganicDashboard, nextOrganicActionState, sanitizePublicTraceability } from '../organicExperience';
import type { OrganicPlanAction } from '../integrationTypes';

const action = (kind: OrganicPlanAction['kind'], state: OrganicPlanAction['state'] = 'ready'): OrganicPlanAction => ({ id: `${kind}-1`, kind, title: kind, description: 'reviewed', priority: 1, state, dueAt: null, source: { organization: 'TNAU', reference: 'ref', url: null, reviewStatus: 'verified' }, sourceActionId: `${kind}-source`, scoutingOnly: kind === 'satellite' });

describe('organic mobile experience contracts', () => {
  it('creates every requested dashboard widget without synthetic content', () => {
    const dashboard = buildOrganicDashboard([action('disease'), action('soil'), action('calendar'), action('weather', 'waiting_for_weather'), action('satellite')]);
    expect(dashboard.map((widget) => widget.kind)).toEqual(['disease', 'soil', 'calendar', 'weather', 'satellite']);
    expect(dashboard.find((widget) => widget.kind === 'weather')?.blocked).toBe(1);
  });
  it('requires a finding before satellite scouting can complete', () => {
    expect(nextOrganicActionState(action('satellite'), 'complete')).toBe('needs_confirmation');
    expect(nextOrganicActionState(action('satellite'), 'finding_recorded')).toBe('completed');
    expect(nextOrganicActionState(action('weather', 'waiting_for_weather'), 'complete')).toBe('waiting_for_weather');
    expect(nextOrganicActionState(action('weather', 'waiting_for_weather'), 'rescheduled')).toBe('ready');
  });
  it('shares only fields explicitly enabled by the farmer', () => {
    expect(sanitizePublicTraceability({ batchCode: 'B1', classification: 'under_organic_transition', verification: 'self_declared', farmerName: 'Private', location: 'Private village', evidenceUrls: ['private'], share: { classification: true, location: false, evidence: false } })).toEqual({ batchCode: 'B1', classification: 'under_organic_transition', verification: 'self_declared' });
  });
});
