import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { farmKeys } from '../constants';
import { addFarmTeamMember, listFarmTeam, removeFarmTeamMember } from '../services/farmTeamApi';

export function useFarmTeam(farmId: string) {
  return useQuery({ queryKey: farmKeys.team(farmId), queryFn: () => listFarmTeam(farmId) });
}

export function useAddFarmTeamMember(farmId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: addFarmTeamMember.bind(null, farmId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: farmKeys.team(farmId) }),
  });
}

export function useRemoveFarmTeamMember(farmId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => removeFarmTeamMember(farmId, memberId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: farmKeys.team(farmId) }),
  });
}
