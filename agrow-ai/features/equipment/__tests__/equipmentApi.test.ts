jest.mock('@/config/internalTestFlags', () => ({ internalTestFlags: { internalFeatureTesting: true } }));
jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn(), post: jest.fn(), patch: jest.fn() } }));
import { api } from '@/services/apiClient';
import { createEquipment, requestEquipment } from '../equipmentApi';

test('creates controlled listing with payments disabled', async () => {
  (api.post as jest.Mock).mockResolvedValue({ test_mode: true, payments_supported: false });
  await createEquipment({ name: 'Tractor', equipment_type: 'tractor' });
  expect(api.post).toHaveBeenCalledWith('/equipment-controlled', { name: 'Tractor', equipment_type: 'tractor' });
});

test('sends a farm-scoped date request and preserves no-payment status', async () => {
  (api.post as jest.Mock).mockResolvedValue({ test_mode: true, payment_status: 'not_supported' });
  const result = await requestEquipment('listing-1', { farm_id: 'farm-1', start_date: '2026-08-14', end_date: '2026-08-15' });
  expect(result.payment_status).toBe('not_supported');
  expect(api.post).toHaveBeenCalledWith('/equipment-controlled/listing-1/requests', expect.objectContaining({ farm_id: 'farm-1' }));
});
