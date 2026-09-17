import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  NotificationItem,
  NotificationListParams,
  NotificationListResult,
  NotificationPreferences,
  NotificationPreferencesPatch,
} from '../types';
import { buildSampleNotifications } from './notificationSamples';
import { DEFAULT_PREFERENCES } from './notificationMapper';
import { NotificationError, type NotificationProvider } from './notificationProvider';
import { notificationStorage } from './notificationStorage';

/**
 * Local, offline notification provider. Seeds a deterministic, rule-classified
 * feed (the client engine mirror) into MMKV and serves reads/mutations from it,
 * so the Notification Center is fully usable in dev / without a backend. It never
 * fabricates data — the feed is representative sample content only.
 */
function ensureSeeded(): void {
  if (notificationStorage.hasLocal()) return;
  notificationStorage.upsertManyLocal(buildSampleNotifications());
}

function isLive(item: NotificationItem, now: string): boolean {
  return item.expiresAt === null || item.expiresAt > now;
}

function paginate(
  items: NotificationItem[],
  page: number,
  pageSize: number,
): NotificationListResult {
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page,
    pageSize,
    total: items.length,
    totalPages: Math.max(1, Math.ceil(items.length / pageSize)),
  };
}

function matches(item: NotificationItem, params: NotificationListParams): boolean {
  if (params.module && item.module !== params.module) return false;
  if (params.severity && item.severity !== params.severity) return false;
  if (params.unread && item.read) return false;
  return true;
}

function readPrefs(): NotificationPreferences {
  return notificationStorage.getPreferences() ?? DEFAULT_PREFERENCES;
}

export const localNotificationProvider: NotificationProvider = {
  async list(params: NotificationListParams): Promise<NotificationListResult> {
    ensureSeeded();
    const now = new Date().toISOString();
    const rows = notificationStorage
      .localNotifications()
      .filter((n) => isLive(n, now) && matches(n, params));
    return paginate(rows, params.page ?? 1, params.pageSize ?? DEFAULT_PAGE_SIZE);
  },

  async unread(): Promise<number> {
    ensureSeeded();
    const now = new Date().toISOString();
    return notificationStorage
      .localNotifications()
      .filter((n) => isLive(n, now) && !n.read).length;
  },

  async markRead(id: string): Promise<NotificationItem> {
    const item = notificationStorage.getLocal(id);
    if (!item) throw new NotificationError('notification_not_found', 'Notification not found.');
    const next = { ...item, read: true };
    notificationStorage.upsertLocal(next);
    return next;
  },

  async markAllRead(): Promise<number> {
    ensureSeeded();
    const now = new Date().toISOString();
    const unread = notificationStorage
      .localNotifications()
      .filter((n) => isLive(n, now) && !n.read);
    unread.forEach((n) => notificationStorage.upsertLocal({ ...n, read: true }));
    return unread.length;
  },

  async dismiss(id: string): Promise<void> {
    const item = notificationStorage.getLocal(id);
    if (!item) throw new NotificationError('notification_not_found', 'Notification not found.');
    notificationStorage.removeLocal(id);
  },

  async getPreferences(): Promise<NotificationPreferences> {
    return readPrefs();
  },

  async updatePreferences(
    patch: NotificationPreferencesPatch,
  ): Promise<NotificationPreferences> {
    const next = { ...readPrefs(), ...patch };
    notificationStorage.savePreferences(next);
    return next;
  },
};
