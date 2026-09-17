import type { Paginated } from '@/types';

import {
  apiToListResult,
  apiToNotification,
  apiToPreferences,
  preferencesPatchToApi,
} from '../services/notificationMapper';
import type { ApiNotification, ApiNotificationPreferences } from '../types';

const apiNotification: ApiNotification = {
  id: 'n1',
  module: 'disease',
  event_type: 'high_confidence_disease',
  farm_id: 'f1',
  title_key: 'notifications.rules.disease.high_confidence_disease.title',
  message_key: 'notifications.rules.disease.high_confidence_disease.message',
  payload: { disease: 'Blast', confidence: 95 },
  severity: 'critical',
  priority: 'critical',
  action_route: '/disease/n1',
  read: false,
  created_at: '2026-07-11T06:00:00Z',
  scheduled_for: null,
  expires_at: '2026-07-18T06:00:00Z',
};

describe('notificationMapper', () => {
  it('maps an API notification to the domain shape', () => {
    const n = apiToNotification(apiNotification);
    expect(n.eventType).toBe('high_confidence_disease');
    expect(n.farmId).toBe('f1');
    expect(n.payload.disease).toBe('Blast');
    expect(n.actionRoute).toBe('/disease/n1');
    expect(n.read).toBe(false);
  });

  it('maps a paginated list envelope', () => {
    const dto: Paginated<ApiNotification> = {
      items: [apiNotification],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
    };
    const result = apiToListResult(dto);
    expect(result.items).toHaveLength(1);
    expect(result.pageSize).toBe(20);
  });

  it('maps preferences to camelCase', () => {
    const dto: ApiNotificationPreferences = {
      weather_enabled: true,
      disease_enabled: false,
      calendar_enabled: true,
      growth_enabled: true,
      market_enabled: true,
      scheme_enabled: true,
      produce_enabled: true,
      ai_enabled: true,
      system_enabled: true,
      in_app_enabled: true,
      push_enabled: true,
      sms_enabled: false,
      email_enabled: false,
      voice_enabled: false,
      min_severity: 'warning',
      language: 'ta',
    };
    const prefs = apiToPreferences(dto);
    expect(prefs.diseaseEnabled).toBe(false);
    expect(prefs.minSeverity).toBe('warning');
  });

  it('only sends provided fields in a preferences patch', () => {
    const body = preferencesPatchToApi({ weatherEnabled: false, minSeverity: 'critical' });
    expect(body).toEqual({ weather_enabled: false, min_severity: 'critical' });
  });
});
