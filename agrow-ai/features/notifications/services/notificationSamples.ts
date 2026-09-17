import { uuid } from '@/utils/id';

import type { NotificationItem, NotificationModuleKey } from '../types';
import { getRule, messageKey, resolveRoute, titleKey } from './rules';

/**
 * Deterministic client-side notification builder — the local mirror of the
 * backend engine (resolve a rule → materialize a notification). Used by the
 * offline/dev provider so the Notification Center shows real, rule-classified
 * alerts without a backend. No AI; no fabricated data.
 */
export interface CandidateSeed {
  module: NotificationModuleKey;
  eventType: string;
  payload: Record<string, unknown>;
  farmId?: string | null;
  ageMinutes?: number; // how long ago it was created (for a realistic feed)
  read?: boolean;
}

export function buildNotification(seed: CandidateSeed, now = new Date()): NotificationItem | null {
  const rule = getRule(seed.module, seed.eventType);
  if (!rule) return null;
  const created = new Date(now.getTime() - (seed.ageMinutes ?? 0) * 60_000);
  const expiresAt =
    rule.expiresAfterHours != null
      ? new Date(created.getTime() + rule.expiresAfterHours * 3_600_000).toISOString()
      : null;
  return {
    id: uuid(),
    module: seed.module,
    eventType: seed.eventType,
    farmId: seed.farmId ?? null,
    titleKey: titleKey(seed.module, seed.eventType),
    messageKey: messageKey(seed.module, seed.eventType),
    payload: seed.payload,
    severity: rule.severity,
    priority: rule.priority,
    actionRoute: resolveRoute(rule.actionRoute, seed.payload),
    read: seed.read ?? false,
    createdAt: created.toISOString(),
    scheduledFor: null,
    expiresAt,
  };
}

/** A representative, deterministic feed covering every event source (offline/dev). */
export function sampleSeeds(): CandidateSeed[] {
  return [
    {
      module: 'disease',
      eventType: 'high_confidence_disease',
      payload: { report_id: 'sample-disease', disease: 'Leaf blight', crop: 'Paddy', confidence: 93 },
      ageMinutes: 20,
    },
    {
      module: 'weather',
      eventType: 'heavy_rain',
      payload: { code: 'heavy_rain.severe', farm_id: null },
      ageMinutes: 90,
    },
    {
      module: 'calendar',
      eventType: 'today_task',
      payload: { count: 2 },
      ageMinutes: 180,
    },
    {
      module: 'produce',
      eventType: 'harvest_approaching',
      payload: { offer_id: 'sample-offer', crop: 'Paddy', days_left: 3 },
      ageMinutes: 300,
    },
    {
      module: 'schemes',
      eventType: 'scheme_eligible',
      payload: { scheme_id: 'sample-scheme', title: 'PM-KISAN' },
      ageMinutes: 720,
    },
    {
      module: 'market',
      eventType: 'favourite_crop_alert',
      payload: { crop: 'Paddy', market: 'Thanjavur', price: 2050 },
      ageMinutes: 900,
    },
    {
      module: 'growth',
      eventType: 'weekly_reminder',
      payload: { session_id: 'sample-session', week: 2 },
      ageMinutes: 1440,
      read: true,
    },
    {
      module: 'ai',
      eventType: 'follow_up_reminder',
      payload: { conversation_id: 'sample-chat', days: 4 },
      ageMinutes: 2880,
      read: true,
    },
  ];
}

export function buildSampleNotifications(now = new Date()): NotificationItem[] {
  return sampleSeeds()
    .map((seed) => buildNotification(seed, now))
    .filter((n): n is NotificationItem => n !== null);
}
