/**
 * Notifications & Smart Alerts — the event center of AgrowAI
 * (docs/API_CONTRACT.md → NOTIFICATIONS, docs/DATABASE_SCHEMA.md → Notifications).
 *
 * Titles/messages travel as localization *keys* + a payload so the Tamil-first
 * client renders them (docs/PRODUCT_RULES.md → Tamil default). Client-side
 * camelCase mirror of the backend notification schemas.
 */

export type NotificationModuleKey =
  | 'weather'
  | 'disease'
  | 'calendar'
  | 'growth'
  | 'market'
  | 'schemes'
  | 'produce'
  | 'ai'
  | 'experts'
  | 'soil'
  | 'satellite'
  | 'nutrient'
  | 'intelligence'
  | 'organic'
  | 'system';

export type Severity = 'info' | 'warning' | 'critical';

export type Priority = 'low' | 'medium' | 'high' | 'critical';

export interface NotificationItem {
  id: string;
  module: NotificationModuleKey;
  eventType: string;
  farmId: string | null;
  titleKey: string;
  messageKey: string;
  payload: Record<string, unknown>;
  severity: Severity;
  priority: Priority;
  actionRoute: string | null;
  read: boolean;
  createdAt: string;
  scheduledFor: string | null;
  expiresAt: string | null;
}

export interface NotificationListResult {
  items: NotificationItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  cached?: boolean;
}

export interface NotificationListParams {
  module?: NotificationModuleKey | null;
  severity?: Severity | null;
  unread?: boolean;
  page?: number;
  pageSize?: number;
}

export interface NotificationPreferences {
  weatherEnabled: boolean;
  diseaseEnabled: boolean;
  calendarEnabled: boolean;
  growthEnabled: boolean;
  marketEnabled: boolean;
  schemeEnabled: boolean;
  produceEnabled: boolean;
  aiEnabled: boolean;
  systemEnabled: boolean;
  inAppEnabled: boolean;
  pushEnabled: boolean;
  smsEnabled: boolean;
  emailEnabled: boolean;
  voiceEnabled: boolean;
  minSeverity: Severity;
  language: string;
}

export type NotificationPreferencesPatch = Partial<NotificationPreferences>;

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiNotification {
  id: string;
  module: NotificationModuleKey;
  event_type: string;
  farm_id: string | null;
  title_key: string;
  message_key: string;
  payload: Record<string, unknown>;
  severity: Severity;
  priority: Priority;
  action_route: string | null;
  read: boolean;
  created_at: string;
  scheduled_for: string | null;
  expires_at: string | null;
}

export interface ApiUnreadCount {
  unread: number;
}

export interface ApiMarkReadResult {
  updated: number;
}

export interface ApiNotificationPreferences {
  weather_enabled: boolean;
  disease_enabled: boolean;
  calendar_enabled: boolean;
  growth_enabled: boolean;
  market_enabled: boolean;
  scheme_enabled: boolean;
  produce_enabled: boolean;
  ai_enabled: boolean;
  system_enabled: boolean;
  in_app_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  email_enabled: boolean;
  voice_enabled: boolean;
  min_severity: Severity;
  language: string;
}
