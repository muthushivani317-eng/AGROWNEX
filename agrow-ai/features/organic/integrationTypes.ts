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
export interface OrganicPlanBundle { farmId: string; actions: OrganicPlanAction[]; generatedAt: string; }
export interface ApiOrganicPlanAction {
  id: string; action_type: OrganicPlanKind; title: string; description: string; priority: number;
  state: OrganicActionState; due_at?: string | null; source_organization: string;
  source_reference: string; source_url?: string | null; review_status: OrganicActionReviewStatus;
  source_action_id: string; scouting_only?: boolean;
}
export interface ApiOrganicPlanBundle { farm_id: string; actions: ApiOrganicPlanAction[]; generated_at: string; }
