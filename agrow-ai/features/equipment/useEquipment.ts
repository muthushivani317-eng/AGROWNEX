import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as service from './equipmentApi';

const keys = { all: ['equipment-controlled'] as const, listings: ['equipment-controlled', 'listings'] as const, requests: ['equipment-controlled', 'requests'] as const };
export const useEquipment = () => useQuery({ queryKey: keys.listings, queryFn: service.listEquipment });
export const useEquipmentRequests = () => useQuery({ queryKey: keys.requests, queryFn: service.listEquipmentRequests });
function mutation<T>(fn: (input: T) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: keys.all }) });
}
export const useCreateEquipment = () => mutation(service.createEquipment);
export const useRequestEquipment = () => mutation<{ listingId: string; farm_id: string; start_date: string; end_date: string; purpose?: string }>(({ listingId, ...input }) => service.requestEquipment(listingId, input));
export const useDecideEquipment = () => mutation<{ requestId: string; decision: 'approved' | 'rejected' }>(({ requestId, decision }) => service.decideEquipmentRequest(requestId, decision));
