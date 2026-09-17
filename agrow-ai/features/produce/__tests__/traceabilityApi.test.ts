jest.mock('@/config/internalTestFlags', () => ({ internalTestFlags: { internalFeatureTesting: true } }));
jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn(), post: jest.fn() } }));
import { api } from '@/services/apiClient';
import { getTraceability, initializeTraceability } from '../traceabilityApi';

const timeline = { batch_id: 'batch', offer_id: 'offer', batch_code: 'AGW-1', events: [], test_mode: true, public_certificate: false, disclaimer: 'Farmer declared' };
test('loads the offer-scoped controlled timeline', async () => {
  (api.get as jest.Mock).mockResolvedValue(timeline);
  await expect(getTraceability('offer')).resolves.toMatchObject({ public_certificate: false });
  expect(api.get).toHaveBeenCalledWith('/produce/offer/traceability-controlled');
});
test('fails closed if backend marks the timeline as a public certificate', async () => {
  (api.post as jest.Mock).mockResolvedValue({ ...timeline, public_certificate: true });
  await expect(initializeTraceability('offer')).rejects.toThrow('TRACEABILITY_SAFETY_CONTRACT_INVALID');
});
