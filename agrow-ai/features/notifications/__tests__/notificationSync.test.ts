jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import type { NotificationProvider } from '../services/notificationProvider';
import { NotificationError } from '../services/notificationProvider';
import {
  isOfflineError,
  notificationOutbox,
  syncNotifications,
} from '../services/notificationSync';

const networkError = () =>
  new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

function fakeProvider(overrides: Partial<NotificationProvider> = {}): NotificationProvider {
  return {
    list: jest.fn(),
    unread: jest.fn(),
    markRead: jest.fn().mockResolvedValue(undefined),
    markAllRead: jest.fn().mockResolvedValue(0),
    dismiss: jest.fn().mockResolvedValue(undefined),
    getPreferences: jest.fn(),
    updatePreferences: jest.fn(),
    ...overrides,
  } as NotificationProvider;
}

describe('notificationSync', () => {
  beforeEach(() => notificationOutbox.clear());

  it('detects offline errors', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new NotificationError('network', 'x'))).toBe(true);
    expect(isOfflineError(new NotificationError('not_found', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('enqueues and drains queued actions on reconnect', async () => {
    notificationOutbox.enqueue({ op: 'read', notificationId: 'n1' });
    notificationOutbox.enqueue({ op: 'dismiss', notificationId: 'n2' });
    notificationOutbox.enqueue({ op: 'readAll' });
    expect(notificationOutbox.count()).toBe(3);

    const provider = fakeProvider();
    const result = await syncNotifications(provider);
    expect(result.synced).toBe(3);
    expect(result.remaining).toBe(0);
    expect(provider.markRead).toHaveBeenCalledWith('n1');
    expect(provider.dismiss).toHaveBeenCalledWith('n2');
    expect(provider.markAllRead).toHaveBeenCalled();
  });

  it('keeps the queue intact while still offline', async () => {
    notificationOutbox.enqueue({ op: 'read', notificationId: 'n1' });
    const provider = fakeProvider({
      markRead: jest.fn().mockRejectedValue(networkError()),
    });
    const result = await syncNotifications(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1); // retained for a later retry
  });

  it('drops a poison entry on a non-network rejection', async () => {
    notificationOutbox.enqueue({ op: 'dismiss', notificationId: 'gone' });
    const provider = fakeProvider({
      dismiss: jest.fn().mockRejectedValue(new NotificationError('not_found', 'x')),
    });
    const result = await syncNotifications(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });
});
