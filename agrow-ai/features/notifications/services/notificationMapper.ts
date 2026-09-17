import type { Paginated } from '@/types';

import type {
  ApiNotification,
  ApiNotificationPreferences,
  NotificationItem,
  NotificationListResult,
  NotificationPreferences,
  NotificationPreferencesPatch,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToNotification(dto: ApiNotification): NotificationItem {
  return {
    id: dto.id,
    module: dto.module,
    eventType: dto.event_type,
    farmId: dto.farm_id,
    titleKey: dto.title_key,
    messageKey: dto.message_key,
    payload: dto.payload ?? {},
    severity: dto.severity,
    priority: dto.priority,
    actionRoute: dto.action_route,
    read: dto.read,
    createdAt: dto.created_at,
    scheduledFor: dto.scheduled_for,
    expiresAt: dto.expires_at,
  };
}

export function apiToListResult(
  dto: Paginated<ApiNotification>,
): NotificationListResult {
  return {
    items: dto.items.map(apiToNotification),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}

export function apiToPreferences(
  dto: ApiNotificationPreferences,
): NotificationPreferences {
  return {
    weatherEnabled: dto.weather_enabled,
    diseaseEnabled: dto.disease_enabled,
    calendarEnabled: dto.calendar_enabled,
    growthEnabled: dto.growth_enabled,
    marketEnabled: dto.market_enabled,
    schemeEnabled: dto.scheme_enabled,
    produceEnabled: dto.produce_enabled,
    aiEnabled: dto.ai_enabled,
    systemEnabled: dto.system_enabled,
    inAppEnabled: dto.in_app_enabled,
    pushEnabled: dto.push_enabled,
    smsEnabled: dto.sms_enabled,
    emailEnabled: dto.email_enabled,
    voiceEnabled: dto.voice_enabled,
    minSeverity: dto.min_severity,
    language: dto.language,
  };
}

/** Domain preference patch → backend request body (camelCase → snake_case). */
export function preferencesPatchToApi(
  patch: NotificationPreferencesPatch,
): Record<string, unknown> {
  const map: Record<keyof NotificationPreferences, string> = {
    weatherEnabled: 'weather_enabled',
    diseaseEnabled: 'disease_enabled',
    calendarEnabled: 'calendar_enabled',
    growthEnabled: 'growth_enabled',
    marketEnabled: 'market_enabled',
    schemeEnabled: 'scheme_enabled',
    produceEnabled: 'produce_enabled',
    aiEnabled: 'ai_enabled',
    systemEnabled: 'system_enabled',
    inAppEnabled: 'in_app_enabled',
    pushEnabled: 'push_enabled',
    smsEnabled: 'sms_enabled',
    emailEnabled: 'email_enabled',
    voiceEnabled: 'voice_enabled',
    minSeverity: 'min_severity',
    language: 'language',
  };
  const body: Record<string, unknown> = {};
  (Object.keys(patch) as (keyof NotificationPreferences)[]).forEach((key) => {
    if (patch[key] !== undefined) body[map[key]] = patch[key];
  });
  return body;
}

export const DEFAULT_PREFERENCES: NotificationPreferences = {
  weatherEnabled: true,
  diseaseEnabled: true,
  calendarEnabled: true,
  growthEnabled: true,
  marketEnabled: true,
  schemeEnabled: true,
  produceEnabled: true,
  aiEnabled: true,
  systemEnabled: true,
  inAppEnabled: true,
  pushEnabled: true,
  smsEnabled: false,
  emailEnabled: false,
  voiceEnabled: false,
  minSeverity: 'info',
  language: 'ta',
};
