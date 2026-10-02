import type { OrganicPlanAction, OrganicPlanKind } from './integrationTypes';

export interface OrganicDashboardWidget { kind: OrganicPlanKind; total: number; ready: number; blocked: number; }
const ORDER: OrganicPlanKind[] = ['disease', 'soil', 'calendar', 'weather', 'satellite'];
export function buildOrganicDashboard(actions: OrganicPlanAction[]): OrganicDashboardWidget[] {
  return ORDER.map((kind) => { const rows = actions.filter((row) => row.kind === kind); return { kind, total: rows.length, ready: rows.filter((row) => row.state === 'ready').length, blocked: rows.filter((row) => row.state === 'waiting_for_weather' || row.state === 'needs_confirmation').length }; });
}
