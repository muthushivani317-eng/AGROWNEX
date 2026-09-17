import type { OrganicActionState, OrganicPlanAction, OrganicPlanKind } from './integrationTypes';

export interface OrganicDashboardWidget { kind: OrganicPlanKind; total: number; ready: number; blocked: number; }
const ORDER: OrganicPlanKind[] = ['disease', 'soil', 'calendar', 'weather', 'satellite'];
export function buildOrganicDashboard(actions: OrganicPlanAction[]): OrganicDashboardWidget[] {
  return ORDER.map((kind) => { const rows = actions.filter((row) => row.kind === kind); return { kind, total: rows.length, ready: rows.filter((row) => row.state === 'ready').length, blocked: rows.filter((row) => row.state === 'waiting_for_weather' || row.state === 'needs_confirmation').length }; });
}
export type OrganicActionEvent = 'complete' | 'rescheduled' | 'finding_recorded';
export function nextOrganicActionState(action: OrganicPlanAction, event: OrganicActionEvent): OrganicActionState {
  if (event === 'rescheduled' && action.state === 'waiting_for_weather') return 'ready';
  if (action.kind === 'satellite') return event === 'finding_recorded' ? 'completed' : 'needs_confirmation';
  if (action.state === 'waiting_for_weather') return 'waiting_for_weather';
  return event === 'complete' ? 'completed' : action.state;
}
export interface TraceabilityPrivacyInput { batchCode: string; classification: string; verification: string; farmerName?: string; location?: string; evidenceUrls?: string[]; share: { classification: boolean; location: boolean; evidence: boolean }; }
export function sanitizePublicTraceability(input: TraceabilityPrivacyInput): Record<string, unknown> {
  return { batchCode: input.batchCode, ...(input.share.classification ? { classification: input.classification, verification: input.verification } : {}), ...(input.share.location && input.location ? { location: input.location } : {}), ...(input.share.evidence ? { evidenceUrls: input.evidenceUrls ?? [] } : {}) };
}
