jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import {
  buildNotification,
  buildSampleNotifications,
} from '../services/notificationSamples';
import { getRule, resolveRoute } from '../services/rules';

describe('notification rules + samples (client engine mirror)', () => {
  it('has a rule for every event source in the brief', () => {
    const events: [string, string][] = [
      ['weather', 'heavy_rain'],
      ['weather', 'low_temperature'],
      ['disease', 'high_confidence_disease'],
      ['calendar', 'today_task'],
      ['growth', 'growth_decline'],
      ['market', 'price_increase'],
      ['schemes', 'application_closing'],
      ['produce', 'harvest_approaching'],
      ['ai', 'follow_up_reminder'],
    ];
    events.forEach(([m, e]) => expect(getRule(m as never, e)).toBeDefined());
  });

  it('resolves an action route from the payload and leaves missing slots intact', () => {
    expect(resolveRoute('/disease/{report_id}', { report_id: 'r1' })).toBe('/disease/r1');
    expect(resolveRoute('/disease/{report_id}', {})).toBe('/disease/{report_id}');
    expect(resolveRoute(null, {})).toBeNull();
  });

  it('builds a notification with rule-derived severity/priority/route/expiry', () => {
    const now = new Date('2026-07-11T06:00:00.000Z');
    const n = buildNotification(
      {
        module: 'disease',
        eventType: 'high_confidence_disease',
        payload: { report_id: 'r1', disease: 'Blight' },
      },
      now,
    );
    expect(n).not.toBeNull();
    expect(n?.severity).toBe('critical');
    expect(n?.priority).toBe('critical');
    expect(n?.actionRoute).toBe('/disease/r1');
    expect(n?.titleKey).toBe('notifications.rules.disease.high_confidence_disease.title');
    expect(n?.expiresAt).toBe(new Date('2026-07-18T06:00:00.000Z').toISOString());
  });

  it('returns null for an unknown event', () => {
    expect(
      buildNotification({ module: 'weather', eventType: 'meteor', payload: {} }),
    ).toBeNull();
  });

  it('builds a representative sample feed', () => {
    const feed = buildSampleNotifications(new Date('2026-07-11T06:00:00.000Z'));
    expect(feed).toHaveLength(8);
    feed.forEach((n) => {
      expect(n.titleKey).toMatch(/\.title$/);
      expect(n.messageKey).toMatch(/\.message$/);
    });
  });
});
