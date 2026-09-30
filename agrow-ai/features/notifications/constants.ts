import type {
  NotificationModuleKey,
  Severity,
} from './types';

export const NOTIFICATION_CACHE_KEY = 'agrowai.notifications.cache';
export const NOTIFICATION_LOCAL_KEY = 'agrowai.notifications.local';
export const NOTIFICATION_PREFS_KEY = 'agrowai.notifications.prefs';
export const NOTIFICATION_OUTBOX_KEY = 'agrowai.notifications.outbox';

export const DEFAULT_PAGE_SIZE = 30;

export const notificationKeys = {
  all: ['notifications'] as const,
  list: (key: string) => ['notifications', 'list', key] as const,
  unread: ['notifications', 'unread'] as const,
  preferences: ['notifications', 'preferences'] as const,
};

/** Modules shown as filter chips (mirrors the backend event sources). */
export const FILTERABLE_MODULES: NotificationModuleKey[] = [
  'weather',
  'disease',
  'calendar',
  'growth',
  'market',
  'schemes',
  'produce',
  'ai',
  'experts',
  'soil',
  'satellite',
  'nutrient',
  'intelligence',
  'organic',
];

export const MODULE_LABEL_KEY: Record<NotificationModuleKey, string> = {
  weather: 'notifications.moduleWeather',
  disease: 'notifications.moduleDisease',
  calendar: 'notifications.moduleCalendar',
  growth: 'notifications.moduleGrowth',
  market: 'notifications.moduleMarket',
  schemes: 'notifications.moduleSchemes',
  produce: 'notifications.moduleProduce',
  ai: 'notifications.moduleAi',
  experts: 'notifications.moduleExperts',
  soil: 'notifications.moduleSoil',
  satellite: 'notifications.moduleSatellite',
  nutrient: 'notifications.moduleNutrient',
  intelligence: 'notifications.moduleIntelligence',
  organic: 'notifications.moduleOrganic',
  system: 'notifications.moduleSystem',
};

export const SEVERITIES: Severity[] = ['info', 'warning', 'critical'];

export const SEVERITY_LABEL_KEY: Record<Severity, string> = {
  info: 'notifications.severityInfo',
  warning: 'notifications.severityWarning',
  critical: 'notifications.severityCritical',
};

export const SEVERITY_TONE: Record<
  Severity,
  'info' | 'warning' | 'danger'
> = {
  info: 'info',
  warning: 'warning',
  critical: 'danger',
};

/** Per-module preference toggles rendered on the Preferences screen. */
export const MODULE_PREFERENCE_FIELDS: {
  module: NotificationModuleKey;
  field:
    | 'weatherEnabled'
    | 'diseaseEnabled'
    | 'calendarEnabled'
    | 'growthEnabled'
    | 'marketEnabled'
    | 'schemeEnabled'
    | 'produceEnabled'
    | 'aiEnabled'
    | 'systemEnabled';
}[] = [
  { module: 'weather', field: 'weatherEnabled' },
  { module: 'disease', field: 'diseaseEnabled' },
  { module: 'calendar', field: 'calendarEnabled' },
  { module: 'growth', field: 'growthEnabled' },
  { module: 'market', field: 'marketEnabled' },
  { module: 'schemes', field: 'schemeEnabled' },
  { module: 'produce', field: 'produceEnabled' },
  { module: 'ai', field: 'aiEnabled' },
];

/** Delivery channels shown on the Preferences screen (in-app always on). */
export const CHANNEL_PREFERENCE_FIELDS: {
  field: 'pushEnabled' | 'smsEnabled' | 'emailEnabled' | 'voiceEnabled';
  labelKey: string;
}[] = [
  { field: 'pushEnabled', labelKey: 'notifications.channelPush' },
  { field: 'smsEnabled', labelKey: 'notifications.channelSms' },
  { field: 'emailEnabled', labelKey: 'notifications.channelEmail' },
  { field: 'voiceEnabled', labelKey: 'notifications.channelVoice' },
];
