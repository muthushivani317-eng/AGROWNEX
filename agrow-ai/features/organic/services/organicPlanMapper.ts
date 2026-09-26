import type { ApiOrganicPlanBundle, OrganicPlanBundle } from '../integrationTypes';

export function apiToOrganicPlanBundle(dto: ApiOrganicPlanBundle): OrganicPlanBundle {
  return { farmId: dto.farm_id, generatedAt: dto.generated_at, actions: dto.actions.map((row) => ({
    id: row.id, kind: row.action_type, title: row.title, description: row.description,
    priority: row.priority, state: row.state, dueAt: row.due_at ?? null,
    source: { organization: row.source_organization, reference: row.source_reference, url: row.source_url ?? null, reviewStatus: row.review_status },
    sourceActionId: row.source_action_id,
    scoutingOnly: row.action_type === 'satellite' ? true : Boolean(row.scouting_only),
  })),
  commonPlanStatus: dto.common_plan_status ?? 'needs_sowing_date',
  commonPlan: (dto.common_plan ?? []).map((step) => ({
    cropCycleId: step.crop_cycle_id, cropId: step.crop_id, week: step.week, dueOn: step.due_on,
    titleTa: step.title_ta, bodyTa: step.body_ta, titleEn: step.title_en, bodyEn: step.body_en,
  })),
  noticeTa: dto.notice_ta, noticeEn: dto.notice_en };
}
