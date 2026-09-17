jest.mock('@/config/internalTestFlags', () => ({ internalTestFlags: { internalFeatureTesting: true } }));
jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn(), post: jest.fn(), delete: jest.fn() } }));

import { api } from '@/services/apiClient';
import { addFarmTeamMember, listFarmTeam } from '../services/farmTeamApi';

test('uses the farm-scoped controlled roster endpoint', async () => {
  (api.get as jest.Mock).mockResolvedValue([]);
  await listFarmTeam('farm-1');
  expect(api.get).toHaveBeenCalledWith('/farms/farm-1/team-controlled');
});

test('accepts only a roster response that cannot grant farm data access', async () => {
  (api.post as jest.Mock).mockResolvedValue({
    id: 'member-1', user_id: 'user-2', phone_number: '+919000000002', role: 'field_worker',
    created_at: '2026-08-13T00:00:00Z', test_mode: true, grants_farm_data_access: false,
  });
  await expect(addFarmTeamMember('farm-1', { phone_number: '+919000000002', role: 'field_worker' }))
    .resolves.toMatchObject({ grants_farm_data_access: false });
});

test('fails closed if a response claims to grant access', async () => {
  (api.post as jest.Mock).mockResolvedValue({ test_mode: true, grants_farm_data_access: true });
  await expect(addFarmTeamMember('farm-1', { phone_number: '+919000000002', role: 'observer' }))
    .rejects.toThrow('FARM_TEAM_SAFETY_CONTRACT_INVALID');
});
