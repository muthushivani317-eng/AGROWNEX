export type OrganicPlanKind = 'disease' | 'soil' | 'calendar' | 'weather' | 'satellite';
export type OrganicActionState = 'ready' | 'waiting_for_weather' | 'needs_confirmation' | 'completed';
export type OrganicActionReviewStatus = 'verified' | 'sourced_public_reference' | 'unverified' | 'farmer_reported';
export interface OrganicSource { organization: string; reference: string; url: string | null; reviewStatus: OrganicActionReviewStatus; }
export interface OrganicPlanAction {
  id: string; kind: OrganicPlanKind; title: string; description: string; priority: number;
  state: OrganicActionState; dueAt: string | null; source: OrganicSource;
  sourceActionId: string; /** Satellite items are scouting prompts only, never diagnoses. */
  scoutingOnly: boolean;
}
export type OrganicCommonPlanStatus = 'ready' | 'no_step_this_week' | 'needs_sowing_date';
export interface OrganicCommonPlanStep { cropCycleId: string; cropId: string; week: number; dueOn: string; titleTa: string; bodyTa: string; titleEn: string; bodyEn: string; }
export interface OrganicPlanBundle {
  farmId: string; actions: OrganicPlanAction[]; generatedAt: string;
  /** Common week-by-week plan (optional: older cached bundles lack it). */
  commonPlanStatus?: OrganicCommonPlanStatus; commonPlan?: OrganicCommonPlanStep[]; noticeTa?: string; noticeEn?: string;
}
export interface ApiOrganicPlanAction {
  id: string; action_type: OrganicPlanKind; title: string; description: string; priority: number;
  state: OrganicActionState; due_at?: string | null; source_organization: string;
  source_reference: string; source_url?: string | null; review_status: OrganicActionReviewStatus;
  source_action_id: string; scouting_only?: boolean;
}
export interface ApiOrganicCommonPlanStep { crop_cycle_id: string; crop_id: string; week: number; due_on: string; title_ta: string; body_ta: string; title_en: string; body_en: string; }
export interface ApiOrganicPlanBundle {
  farm_id: string; actions: ApiOrganicPlanAction[]; generated_at: string;
  common_plan_status?: OrganicCommonPlanStatus; common_plan?: ApiOrganicCommonPlanStep[]; notice_ta?: string; notice_en?: string;
}
