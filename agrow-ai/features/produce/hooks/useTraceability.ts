import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { addTraceEvent, createPublicTraceabilityShare, getTraceability, initializeTraceability, revokePublicTraceabilityShare, type PublicShareConsent } from '../traceabilityApi';
import { uuid } from '@/utils/id';
const key = (id: string) => ['produce', 'traceability-controlled', id] as const;
export const useTraceability = (id: string) => useQuery({ queryKey: key(id), queryFn: () => getTraceability(id) });
export function useInitializeTraceability(id: string) { const client = useQueryClient(); return useMutation({ mutationFn: () => initializeTraceability(id), onSuccess: (data) => client.setQueryData(key(id), data) }); }
export function useAddTraceEvent(id: string) { const client = useQueryClient(); return useMutation({ mutationFn: (input: Parameters<typeof addTraceEvent>[1]) => addTraceEvent(id, input), onSuccess: (data) => client.setQueryData(key(id), data) }); }
export function useCreatePublicTraceabilityShare(id: string) { return useMutation({ mutationFn: (consent: PublicShareConsent) => createPublicTraceabilityShare(id, consent, uuid()) }); }
export function useRevokePublicTraceabilityShare(id: string) { const client = useQueryClient(); return useMutation({ mutationFn: () => revokePublicTraceabilityShare(id, uuid()), onSuccess: () => void client.invalidateQueries({ queryKey: key(id) }) }); }
