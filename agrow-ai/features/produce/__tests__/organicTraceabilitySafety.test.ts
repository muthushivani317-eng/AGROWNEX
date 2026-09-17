import { buildPublicShareRequest, safePublicShareUrl, verifyTraceabilitySafety, type TraceTimeline } from '../traceabilityApi';
const base: TraceTimeline = { batch_id: 'b', offer_id: 'o', batch_code: 'B', events: [], test_mode: true, public_certificate: false, disclaimer: 'Farmer declared' };
describe('organic traceability claim safety', () => {
  it('rejects a certified claim without verified certification', () => expect(() => verifyTraceabilitySafety({ ...base, organic_classification: 'certified_organic', organic_claim_verification: 'self_declared' })).toThrow('ORGANIC_CERTIFICATION_CLAIM_INVALID'));
  it('allows an accurately labelled transition claim', () => expect(verifyTraceabilitySafety({ ...base, organic_classification: 'under_organic_transition', organic_claim_verification: 'self_declared' }).organic_classification).toBe('under_organic_transition'));
  it('requires explicit consent and never sends private evidence implicitly', () => expect(buildPublicShareRequest({ classification: true, events: false }, 'idem-123456')).toEqual({ consent_fields: ['classification'], idempotency_key: 'idem-123456' }));
  it('renders only HTTPS public share URLs', () => { expect(safePublicShareUrl('https://agrow.ai/t/1')).toBe('https://agrow.ai/t/1'); expect(safePublicShareUrl('javascript:alert(1)')).toBeNull(); });
});
