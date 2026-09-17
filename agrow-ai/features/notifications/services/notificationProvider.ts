import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type {
  NotificationItem,
  NotificationListParams,
  NotificationListResult,
  NotificationPreferences,
  NotificationPreferencesPatch,
} from '../types';

/**
 * Notification data source contract. Backed by the AgrowAI notification API +
 * deterministic engine when a backend is configured, otherwise a local offline
 * provider that renders a faithful set of generated alerts from MMKV. Designed so
 * a future delivery channel (FCM, OneSignal, SMS, Email) can join the
 * backend with no frontend change (docs: provider abstraction).
 */
export interface NotificationProvider {
  list(params: NotificationListParams): Promise<NotificationListResult>;
  unread(): Promise<number>;
  markRead(id: string): Promise<NotificationItem>;
  markAllRead(): Promise<number>;
  dismiss(id: string): Promise<void>;
  getPreferences(): Promise<NotificationPreferences>;
  updatePreferences(patch: NotificationPreferencesPatch): Promise<NotificationPreferences>;
}

export class NotificationError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'NotificationError';
  }
}

let provider: NotificationProvider | null = null;

export function getNotificationProvider(): NotificationProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiNotificationProvider')
      .apiNotificationProvider as NotificationProvider;
    logger.info('notifications', 'using api provider');
  } else {
    provider = require('./localNotificationProvider')
      .localNotificationProvider as NotificationProvider;
    logger.info('notifications', 'using local provider');
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setNotificationProvider(next: NotificationProvider | null): void {
  provider = next;
}
