import type { ApiOrganicPlanBundle, OrganicPlanBundle } from '../integrationTypes';

export function apiToOrganicPlanBundle(dto: ApiOrganicPlanBundle): OrganicPlanBundle {
  return { farmId: dto.farm_id, generatedAt: dto.generated_at, actions: dto.actions.map((row) => ({
    id: row.id, kind: row.action_type, title: row.title, description: row.description,
    priority: row.priority, state: row.state, dueAt: row.due_at ?? null,
    source: { organization: row.source_organization, reference: row.source_reference, url: row.source_url ?? null, reviewStatus: row.review_status },
    sourceActionId: row.source_action_id,
    scoutingOnly: row.action_type === 'satellite' ? true : Boolean(row.scouting_only),
  })) };
}
