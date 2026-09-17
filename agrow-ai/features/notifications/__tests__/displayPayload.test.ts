import { notificationDisplayPayload } from '../utils/displayPayload';
import { en } from '@/localization/locales/en';
import { ta } from '@/localization/locales/ta';

it('formats the disease label without mutating evidence or stored identifiers', () => {
  const payload = { disease: 'banana__sigatoka_leaf_spot', confidence: 100, report_id: 'r1' };
  expect(notificationDisplayPayload(payload)).toEqual({ ...payload, disease: 'Sigatoka Leaf Spot' });
  expect(payload.disease).toBe('banana__sigatoka_leaf_spot');
});
it('provides the home action label in both supported languages', () => {
  expect(en.common.viewDetails).toBe('View details');
  expect(ta.common.viewDetails).toBe('விவரங்களைக் காண்க');
});
