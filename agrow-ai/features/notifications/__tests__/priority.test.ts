import { selectTopPriority } from '../utils/priority';
import type { NotificationItem } from '../types';

function item(
  overrides: Partial<NotificationItem> & Pick<NotificationItem, 'id'>,
): NotificationItem {
  return {
    module: 'weather',
    eventType: 'test',
    farmId: null,
    titleKey: 'notifications.test.title',
    messageKey: 'notifications.test.message',
    payload: {},
    severity: 'info',
    priority: 'low',
    actionRoute: null,
    read: false,
    createdAt: '2026-08-09T00:00:00.000Z',
    scheduledFor: null,
    expiresAt: null,
    ...overrides,
  };
}

describe('selectTopPriority', () => {
  it('prefers priority over severity', () => {
    const highPriority = item({ id: 'high', priority: 'high', severity: 'info' });
    const severe = item({ id: 'severe', priority: 'medium', severity: 'critical' });

    expect(selectTopPriority([severe, highPriority])).toBe(highPriority);
  });

  it('uses severity before recency', () => {
    const severe = item({
      id: 'severe',
      priority: 'high',
      severity: 'critical',
      createdAt: '2026-08-08T00:00:00.000Z',
    });
    const recent = item({
      id: 'recent',
      priority: 'high',
      severity: 'warning',
      createdAt: '2026-08-09T00:00:00.000Z',
    });

    expect(selectTopPriority([recent, severe])).toBe(severe);
  });

  it('uses recency before id', () => {
    const older = item({ id: 'a', createdAt: '2026-08-08T00:00:00.000Z' });
    const newer = item({ id: 'z', createdAt: '2026-08-09T00:00:00.000Z' });

    expect(selectTopPriority([older, newer])).toBe(newer);
  });

  it('returns null for an empty array', () => {
    expect(selectTopPriority([])).toBeNull();
  });
});
