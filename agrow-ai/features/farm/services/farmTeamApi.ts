import { internalTestFlags } from '@/config/internalTestFlags';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

export type FarmTeamRole = 'manager' | 'field_worker' | 'agronomist' | 'observer';
export interface FarmTeamMember {
  id: string;
  user_id: string;
  phone_number: string;
  role: FarmTeamRole;
  created_at: string;
  test_mode: true;
  grants_farm_data_access: false;
}

function requireInternalBuild() {
  if (!internalTestFlags.internalFeatureTesting) throw new Error('CONTROLLED_TEST_BUILD_REQUIRED');
}

export async function listFarmTeam(farmId: string): Promise<FarmTeamMember[]> {
  requireInternalBuild();
  return api.get<FarmTeamMember[]>(endpoints.farms.team(farmId));
}

export async function addFarmTeamMember(
  farmId: string,
  input: { phone_number: string; role: FarmTeamRole },
): Promise<FarmTeamMember> {
  requireInternalBuild();
  const member = await api.post<FarmTeamMember>(endpoints.farms.team(farmId), input);
  if (member.test_mode !== true || member.grants_farm_data_access !== false) {
    throw new Error('FARM_TEAM_SAFETY_CONTRACT_INVALID');
  }
  return member;
}

export async function removeFarmTeamMember(farmId: string, memberId: string): Promise<void> {
  requireInternalBuild();
  await api.delete<null>(endpoints.farms.teamMember(farmId, memberId));
}
