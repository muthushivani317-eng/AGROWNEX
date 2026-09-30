import type { NotificationModuleKey, Priority, Severity } from "../types";

/**
 * Client-side mirror of the backend notification rule table
 * (backend: app/modules/notifications/constants.RULES). Deterministic, no AI —
 * so the local/offline provider classifies severity/priority/route exactly like
 * the server (docs: RULE ENGINE). One entry per event source in the module brief.
 */
export interface NotificationRule {
  module: NotificationModuleKey;
  eventType: string;
  severity: Severity;
  priority: Priority;
  expiresAfterHours: number | null;
  actionRoute: string | null;
}

function rule(
  module: NotificationModuleKey,
  eventType: string,
  severity: Severity,
  priority: Priority,
  expiresAfterHours: number | null,
  actionRoute: string | null,
): NotificationRule {
  return {
    module,
    eventType,
    severity,
    priority,
    expiresAfterHours,
    actionRoute,
  };
}

const LIST: NotificationRule[] = [
  // Weather
  rule("weather", "heavy_rain", "warning", "high", 24, "/weather"),
  rule("weather", "high_wind", "warning", "medium", 24, "/weather"),
  rule("weather", "extreme_heat", "warning", "high", 24, "/weather"),
  rule("weather", "low_temperature", "warning", "medium", 24, "/weather"),
  // Disease
  rule(
    "disease",
    "high_confidence_disease",
    "critical",
    "critical",
    168,
    "/disease/{report_id}",
  ),
  rule(
    "disease",
    "expert_review_needed",
    "warning",
    "high",
    168,
    "/disease/{report_id}",
  ),
  rule("disease", "poor_image_quality", "info", "low", 48, "/disease"),
  rule(
    "disease",
    "disease_risk_conditions",
    "warning",
    "medium",
    24,
    "/disease-risk",
  ),
  // Crop Calendar
  rule("calendar", "today_task", "info", "high", 36, "/calendar"),
  rule("calendar", "upcoming_task", "info", "medium", 96, "/calendar"),
  rule("calendar", "missed_activity", "warning", "high", 168, "/calendar"),
  // Growth Monitor
  rule("growth", "weekly_reminder", "info", "medium", 168, "/growth"),
  rule("growth", "growth_decline", "warning", "high", 168, "/growth"),
  rule("growth", "growth_improvement", "info", "low", 168, "/growth"),
  // Market
  rule("market", "price_increase", "info", "medium", 48, "/market"),
  rule("market", "price_decrease", "warning", "medium", 48, "/market"),
  rule("market", "favourite_crop_alert", "info", "medium", 48, "/market"),
  // Government Schemes
  rule(
    "schemes",
    "scheme_eligible",
    "info",
    "medium",
    336,
    "/schemes/{scheme_id}",
  ),
  rule(
    "schemes",
    "application_closing",
    "warning",
    "high",
    240,
    "/schemes/{scheme_id}",
  ),
  rule("schemes", "new_scheme", "info", "low", 336, "/schemes"),
  // Sell My Produce
  rule(
    "produce",
    "offer_submitted",
    "info",
    "medium",
    72,
    "/produce/{offer_id}",
  ),
  rule(
    "produce",
    "harvest_approaching",
    "info",
    "high",
    336,
    "/produce/{offer_id}",
  ),
  rule("produce", "buyer_interest", "info", "high", 336, "/produce/{offer_id}"),
  rule(
    "produce",
    "offer_expiring",
    "warning",
    "high",
    168,
    "/produce/{offer_id}",
  ),
  // AI
  rule("ai", "follow_up_reminder", "info", "low", 168, "/ai"),
  rule("ai", "conversation_reminder", "info", "low", 168, "/ai"),
  // Organic -- reminder to log a suggested organic action before it goes stale
  rule(
    "organic",
    "practice_not_logged",
    "info",
    "medium",
    168,
    "/organic/plan?farmId={farm_id}",
  ),
];

export const RULES: Record<string, NotificationRule> = Object.fromEntries(
  LIST.map((r) => [`${r.module}:${r.eventType}`, r]),
);

export function getRule(
  module: NotificationModuleKey,
  eventType: string,
): NotificationRule | undefined {
  return RULES[`${module}:${eventType}`];
}

/** Fill {placeholder} slots in an action route from a payload (never throws). */
export function resolveRoute(
  template: string | null,
  payload: Record<string, unknown>,
): string | null {
  if (!template) return null;
  return template.replace(/\{(\w+)\}/g, (match, key) => {
    const value = payload[key];
    return value === undefined || value === null ? match : String(value);
  });
}

export function titleKey(
  module: NotificationModuleKey,
  eventType: string,
): string {
  return `notifications.rules.${module}.${eventType}.title`;
}

export function messageKey(
  module: NotificationModuleKey,
  eventType: string,
): string {
  return `notifications.rules.${module}.${eventType}.message`;
}
