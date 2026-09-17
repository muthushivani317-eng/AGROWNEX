import { internalTestFlags } from '@/config/internalTestFlags';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

export type EquipmentType = 'tractor' | 'tiller' | 'harvester' | 'sprayer' | 'pump' | 'other';
export interface EquipmentListing { id: string; owner_user_id: string; name: string; equipment_type: EquipmentType; district: string | null; description: string | null; status: string; created_at: string; test_mode: true; payments_supported: false }
export interface EquipmentRequest { id: string; listing_id: string; equipment_name: string; requester_user_id: string; farm_id: string; start_date: string; end_date: string; purpose: string | null; status: string; decision_note: string | null; created_at: string; test_mode: true; payment_status: 'not_supported'; can_decide: boolean; is_requester: boolean }

function requireControlled() {
  if (!internalTestFlags.internalFeatureTesting) throw new Error('CONTROLLED_TEST_BUILD_REQUIRED');
}
function verify<T extends { test_mode: true }>(value: T): T {
  if (value.test_mode !== true) throw new Error('EQUIPMENT_SAFETY_CONTRACT_INVALID');
  return value;
}
export async function listEquipment(): Promise<EquipmentListing[]> { requireControlled(); return api.get(endpoints.equipment.root); }
export async function createEquipment(input: { name: string; equipment_type: EquipmentType; district?: string; description?: string }): Promise<EquipmentListing> { requireControlled(); return verify(await api.post(endpoints.equipment.root, input)); }
export async function requestEquipment(listingId: string, input: { farm_id: string; start_date: string; end_date: string; purpose?: string }): Promise<EquipmentRequest> { requireControlled(); return verify(await api.post(endpoints.equipment.requests(listingId), input)); }
export async function listEquipmentRequests(): Promise<EquipmentRequest[]> { requireControlled(); return api.get(endpoints.equipment.mine); }
export async function decideEquipmentRequest(requestId: string, decision: 'approved' | 'rejected'): Promise<EquipmentRequest> { requireControlled(); return verify(await api.patch(endpoints.equipment.decision(requestId), { decision })); }
