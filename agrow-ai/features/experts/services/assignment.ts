import type { ExpertDetail } from '../types';

/**
 * Client-side mirror of the backend Expert Engine's deterministic assignment
 * (backend: app/modules/experts/engine.assign_expert). Same transparent weights,
 * so the local/offline provider routes a consultation to the same kind of desk.
 * No AI — every choice is explainable.
 */
const SCORE_CATEGORY_MATCH = 40;
const SCORE_CROP_MATCH = 20;
const SCORE_DISTRICT_MATCH = 20;
const SCORE_LANGUAGE_MATCH = 10;
const SCORE_VERIFIED = 10;
const SCORE_AVAILABLE = 5;
const SCORE_GENERALIST = 8;

export interface AssignmentContext {
  category: string;
  crop?: string | null;
  district?: string | null;
  language?: string | null;
}

const norm = (v: string | null | undefined): string => (v ?? '').trim().toLowerCase();

export function scoreExpert(expert: ExpertDetail, ctx: AssignmentContext): number {
  let score = 0;
  const categories = expert.categories.map(norm);
  const isGeneralist = expert.districts.length === 0;

  if (categories.includes(norm(ctx.category))) {
    score += SCORE_CATEGORY_MATCH;
  } else if (isGeneralist || categories.includes('general')) {
    score += SCORE_GENERALIST;
  }

  const crops = expert.specializations
    .map((s) => norm(s.crop))
    .filter(Boolean);
  if (ctx.crop && crops.includes(norm(ctx.crop))) score += SCORE_CROP_MATCH;

  const districts = expert.districts.map(norm);
  if (ctx.district && districts.includes(norm(ctx.district))) score += SCORE_DISTRICT_MATCH;

  const languages = expert.languages.map(norm);
  if (ctx.language && languages.includes(norm(ctx.language))) score += SCORE_LANGUAGE_MATCH;

  if (expert.verified) score += SCORE_VERIFIED;
  score += SCORE_AVAILABLE; // local desks are always available

  return score;
}

/** Pick the best-matching verified desk deterministically (tie-break by id). */
export function assignExpert(
  experts: ExpertDetail[],
  ctx: AssignmentContext,
): ExpertDetail | null {
  const eligible = experts.filter((e) => e.verified);
  if (eligible.length === 0) return null;
  return [...eligible].sort((a, b) => {
    const diff = scoreExpert(b, ctx) - scoreExpert(a, ctx);
    return diff !== 0 ? diff : a.id.localeCompare(b.id);
  })[0];
}
