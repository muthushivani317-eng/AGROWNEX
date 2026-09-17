/**
 * Local eligibility engine — a faithful, deterministic mirror of the backend
 * ``app/modules/schemes/engine.py``. Used by the offline / local provider so the
 * app produces the same transparent verdicts and scores without a backend. Pure:
 * no I/O, no side effects.
 */
import { DEFAULT_STATE } from '../constants';
import type {
  Eligibility,
  EligibilityStatus,
  FarmerCategory,
  SchemeQuery,
} from '../types';

const ANY = 'all';

const OPEN = 'open';
const MATCH = 'match';
const FAIL = 'fail';
const UNKNOWN = 'unknown';

const CRITERIA = ['state', 'district', 'crop', 'category', 'land', 'income'] as const;

/** Structured rules a scheme is evaluated against (["all"] = no constraint). */
export interface SchemeRules {
  states: string[];
  districts: string[];
  crops: string[];
  farmerCategories: string[];
  minLandHectares: number | null;
  maxLandHectares: number | null;
  maxAnnualIncome: number | null;
  status: 'active' | 'closed';
  /**
   * ISO date string; application deadline, or null/undefined if open-ended.
   * Optional because callers typically keep this on a separate top-level
   * `lastDate` field on the scheme record (mirroring the backend's
   * GovernmentScheme model) and merge it in at the `evaluate()` call site.
   */
  lastDate?: string | null;
}

export interface FarmerContext {
  state: string | null;
  district: string | null;
  crop: string | null;
  landHectares: number | null;
  annualIncome: number | null;
  farmerCategory: FarmerCategory | null;
}

/** Land-holding class thresholds (hectares), matching the backend classification. */
export function deriveFarmerCategory(
  landHectares: number | null | undefined,
): FarmerCategory | null {
  if (landHectares == null || landHectares <= 0) return null;
  if (landHectares < 1) return 'marginal';
  if (landHectares < 2) return 'small';
  if (landHectares < 4) return 'semi_medium';
  if (landHectares < 10) return 'medium';
  return 'large';
}

/** Build the farmer context from a query, defaulting the state (Tamil-Nadu-first). */
export function contextFromQuery(query: SchemeQuery): FarmerContext {
  const land = query.landHectares ?? null;
  return {
    state: query.state ?? DEFAULT_STATE,
    district: query.district ?? null,
    crop: query.crop ?? null,
    landHectares: land,
    annualIncome: query.annualIncome ?? null,
    farmerCategory: query.farmerCategory ?? deriveFarmerCategory(land),
  };
}

function norm(value: string): string {
  return value.trim().toLowerCase();
}

function listOutcome(allowed: string[], value: string | null): string {
  if (allowed.length === 0 || allowed.some((a) => norm(a) === ANY)) return OPEN;
  if (value == null || !String(value).trim()) return UNKNOWN;
  const set = new Set(allowed.map(norm));
  return set.has(norm(String(value))) ? MATCH : FAIL;
}

function landOutcome(
  min: number | null,
  max: number | null,
  land: number | null,
): string {
  if (min == null && max == null) return OPEN;
  if (land == null) return UNKNOWN;
  if (min != null && land < min) return FAIL;
  if (max != null && land > max) return FAIL;
  return MATCH;
}

function incomeOutcome(max: number | null, income: number | null): string {
  if (max == null) return OPEN;
  if (income == null) return UNKNOWN;
  return income <= max ? MATCH : FAIL;
}

/** Transparent 0-100 score: targeted matches raise it, unknowns lower it. */
function score(matched: string[], unknown: string[]): number {
  const raw = 55 + 12 * matched.length - 8 * unknown.length;
  return Math.max(10, Math.min(100, raw));
}

/**
 * Evaluate a scheme for a farmer (pure — ``today`` is passed in by the
 * caller rather than read from the clock, mirroring the backend's
 * ``app/modules/schemes/engine.py::evaluate``). A scheme whose application
 * window has already closed (``lastDate`` in the past) is treated like a
 * closed scheme: not_eligible, never surfaced as eligible/likely-eligible,
 * no matter how well the farmer otherwise matches. Omitting ``today``
 * skips the deadline check (old behaviour), so any caller not yet updated
 * keeps working.
 */
export function evaluate(
  rules: SchemeRules,
  context: FarmerContext,
  today: Date | null = null,
): Eligibility {
  const categoryValue = context.farmerCategory ?? null;
  const outcomes: Record<string, string> = {
    state: listOutcome(rules.states, context.state),
    district: listOutcome(rules.districts, context.district),
    crop: listOutcome(rules.crops, context.crop),
    category: listOutcome(rules.farmerCategories, categoryValue),
    land: landOutcome(rules.minLandHectares, rules.maxLandHectares, context.landHectares),
    income: incomeOutcome(rules.maxAnnualIncome, context.annualIncome),
  };

  const matched = CRITERIA.filter((c) => outcomes[c] === MATCH);
  let unmet = CRITERIA.filter((c) => outcomes[c] === FAIL) as string[];
  const unknown = CRITERIA.filter((c) => outcomes[c] === UNKNOWN);

  const expired =
    rules.lastDate != null && today != null && today.getTime() > new Date(rules.lastDate).getTime();
  if (expired) unmet = [...unmet, 'deadline'];

  if (rules.status === 'closed' || expired || unmet.length > 0) {
    return { status: 'not_eligible', score: 0, matched, unmet, unknown };
  }

  const status: EligibilityStatus = unknown.length > 0 ? 'likely_eligible' : 'eligible';
  return { status, score: score(matched, unknown), matched, unmet, unknown };
}

export function isEligible(result: Eligibility): boolean {
  return result.status !== 'not_eligible';
}

const STATUS_ORDER: Record<EligibilityStatus, number> = {
  eligible: 0,
  likely_eligible: 1,
  not_eligible: 2,
};

/** Rank: eligible first, then higher score, then the soonest deadline. */
export function rank<T extends { lastDate: string | null; eligibility: Eligibility }>(
  items: T[],
): T[] {
  return [...items].sort((a, b) => {
    const statusDiff =
      STATUS_ORDER[a.eligibility.status] - STATUS_ORDER[b.eligibility.status];
    if (statusDiff !== 0) return statusDiff;
    const scoreDiff = b.eligibility.score - a.eligibility.score;
    if (scoreDiff !== 0) return scoreDiff;
    // Schemes with a deadline sort before open-ended ones; sooner first.
    const ak = a.lastDate ? new Date(a.lastDate).getTime() : Infinity;
    const bk = b.lastDate ? new Date(b.lastDate).getTime() : Infinity;
    return ak - bk;
  });
}
