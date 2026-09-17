jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localNotificationProvider } from '../services/localNotificationProvider';
import { NotificationError } from '../services/notificationProvider';
import { notificationStorage } from '../services/notificationStorage';

describe('localNotificationProvider', () => {
  beforeEach(() => notificationStorage.clear());

  it('seeds a deterministic feed covering every event source on first list', async () => {
    const page = await localNotificationProvider.list({});
    expect(page.total).toBe(8);
    const modules = new Set(page.items.map((n) => n.module));
    expect(modules).toEqual(
      new Set(['weather', 'disease', 'calendar', 'growth', 'market', 'schemes', 'produce', 'ai']),
    );
  });

  it('filters by module and severity', async () => {
    const disease = await localNotificationProvider.list({ module: 'disease' });
    expect(disease.total).toBe(1);
    expect(disease.items[0].eventType).toBe('high_confidence_disease');

    const critical = await localNotificationProvider.list({ severity: 'critical' });
    expect(critical.items.every((n) => n.severity === 'critical')).toBe(true);
    expect(critical.total).toBe(1);
  });

  it('counts unread and filters unread-only', async () => {
    // Two seeds (growth, ai) start read → 6 unread.
    expect(await localNotificationProvider.unread()).toBe(6);
    const unread = await localNotificationProvider.list({ unread: true });
    expect(unread.total).toBe(6);
    expect(unread.items.every((n) => !n.read)).toBe(true);
  });

  it('marks a notification read', async () => {
    const page = await localNotificationProvider.list({ unread: true });
    const target = page.items[0];
    const updated = await localNotificationProvider.markRead(target.id);
    expect(updated.read).toBe(true);
    expect(await localNotificationProvider.unread()).toBe(5);
  });

  it('marks all read', async () => {
    const count = await localNotificationProvider.markAllRead();
    expect(count).toBe(6);
    expect(await localNotificationProvider.unread()).toBe(0);
  });

  it('dismisses a notification', async () => {
    const page = await localNotificationProvider.list({});
    const target = page.items[0];
    await localNotificationProvider.dismiss(target.id);
    const after = await localNotificationProvider.list({});
    expect(after.total).toBe(7);
    await expect(localNotificationProvider.markRead(target.id)).rejects.toBeInstanceOf(
      NotificationError,
    );
  });

  it('reads and updates preferences (partial)', async () => {
    const prefs = await localNotificationProvider.getPreferences();
    expect(prefs.weatherEnabled).toBe(true);
    const updated = await localNotificationProvider.updatePreferences({
      weatherEnabled: false,
      minSeverity: 'warning',
    });
    expect(updated.weatherEnabled).toBe(false);
    expect(updated.minSeverity).toBe('warning');
    expect(updated.diseaseEnabled).toBe(true); // untouched
  });
});
