import { internalTestFlags } from '@/config/internalTestFlags';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

export type TraceEventType = 'sowing_recorded' | 'input_applied' | 'harvested' | 'graded' | 'packed' | 'stored' | 'transported' | 'handover';
export type OrganicProduceClassification = 'conventional' | 'organic_practices_not_certified' | 'under_organic_transition' | 'certified_organic';
export type OrganicClaimVerification = 'not_claimed' | 'self_declared' | 'document_submitted' | 'verified' | 'expired' | 'rejected';
export interface TraceEvent { id: string; event_type: TraceEventType; occurred_at: string; location_text: string | null; notes: string | null; evidence_url: string | null; event_hash: string; created_at: string; declared_by_farmer: true; independently_verified: false }
export interface TraceTimeline { batch_id: string; offer_id: string; batch_code: string; events: TraceEvent[]; test_mode: true; public_certificate: false; disclaimer: string; organic_classification?: OrganicProduceClassification; organic_claim_verification?: OrganicClaimVerification; public_share_url?: string | null; qr_code_url?: string | null }
export interface PublicShareConsent { classification: boolean; events: boolean }
export interface PublicTraceabilityShare { share_url: string; qr_payload: string; consent_fields: Array<'classification' | 'events'> }
export function buildPublicShareRequest(consent: PublicShareConsent, idempotencyKey: string) { const consent_fields: PublicTraceabilityShare['consent_fields'] = []; if (consent.classification) consent_fields.push('classification'); if (consent.events) consent_fields.push('events'); return { consent_fields, idempotency_key: idempotencyKey }; }
export function safePublicShareUrl(value: string | null | undefined): string | null { if (!value) return null; try { const url = new URL(value); return url.protocol === 'https:' ? value : null; } catch { return null; } }

function controlled() { if (!internalTestFlags.internalFeatureTesting) throw new Error('CONTROLLED_TEST_BUILD_REQUIRED'); }
export function verifyTraceabilitySafety(value: TraceTimeline): TraceTimeline {
  if (value.test_mode !== true || value.public_certificate !== false || value.events.some((event) => event.independently_verified !== false)) throw new Error('TRACEABILITY_SAFETY_CONTRACT_INVALID');
  if (value.organic_classification === 'certified_organic' && value.organic_claim_verification !== 'verified') throw new Error('ORGANIC_CERTIFICATION_CLAIM_INVALID');
  return value;
}
export async function getTraceability(offerId: string): Promise<TraceTimeline | null> { controlled(); const value = await api.get<TraceTimeline | null>(endpoints.produce.traceability(offerId)); return value ? verifyTraceabilitySafety(value) : null; }
export async function initializeTraceability(offerId: string): Promise<TraceTimeline> { controlled(); return verifyTraceabilitySafety(await api.post(endpoints.produce.traceabilityInitialize(offerId))); }
export async function addTraceEvent(offerId: string, input: { event_type: TraceEventType; occurred_at: string; location_text?: string; notes?: string }): Promise<TraceTimeline> { controlled(); return verifyTraceabilitySafety(await api.post(endpoints.produce.traceabilityEvents(offerId), input)); }
export async function createPublicTraceabilityShare(offerId: string, consent: PublicShareConsent, idempotencyKey: string): Promise<PublicTraceabilityShare> { controlled(); return api.post(endpoints.produce.traceabilityPublicShare(offerId), buildPublicShareRequest(consent, idempotencyKey)); }
export async function revokePublicTraceabilityShare(offerId: string, idempotencyKey: string): Promise<void> { controlled(); await api.post(endpoints.produce.traceabilityPublicShareRevoke(offerId), { idempotency_key: idempotencyKey }); }
