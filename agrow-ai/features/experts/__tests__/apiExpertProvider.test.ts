// Gate coverage for apiExpertProvider (2026-08-18 pre-release audit): "Ask an
// Expert" was previously reachable in production with no readiness gate at
// all, unlike features/equipment and features/community which both fail
// closed outside a controlled test build. These tests cover both states of
// that gate using jest.doMock + resetModules, since the flag needs to differ
// between tests (unlike the equipment/community tests, which only ever
// exercise the "enabled" branch). Both `api` and the provider are re-required
// together after each reset so the test asserts against the same mock
// instance the provider actually calls.
jest.mock('@/services/apiClient', () => ({
  api: { get: jest.fn(), post: jest.fn(), put: jest.fn() },
}));
jest.mock('../services/expertMapper', () => ({
  apiToExpert: jest.fn((x: unknown) => x),
  apiToExpertDetail: jest.fn((x: unknown) => x),
  apiToExpertList: jest.fn((x: unknown) => x),
  apiToConsultation: jest.fn((x: unknown) => x),
  apiToConsultationDetail: jest.fn((x: unknown) => x),
  apiToConsultationList: jest.fn((x: unknown) => x),
  consultationInputToApi: jest.fn((x: unknown) => x),
  attachmentToApi: jest.fn((x: unknown) => x),
  replyInputToApi: jest.fn((x: unknown) => x),
}));
jest.mock('../services/expertStorage', () => ({
  expertListKey: jest.fn(() => 'experts-key'),
  consultationListKey: jest.fn(() => 'consultations-key'),
  expertStorage: {
    cacheExpertList: jest.fn(),
    getCachedExpertList: jest.fn(),
    cacheConsultationList: jest.fn(),
    getCachedConsultationList: jest.fn(),
  },
}));

import type * as ApiClientModule from '@/services/apiClient';
import type * as ApiExpertProviderModule from '../services/apiExpertProvider';

function load(internalFeatureTesting: boolean) {
  jest.resetModules();
  jest.doMock('@/config/internalTestFlags', () => ({
    internalTestFlags: { internalFeatureTesting },
  }));
  const api: typeof ApiClientModule.api = require('@/services/apiClient').api;
  const provider: typeof ApiExpertProviderModule.apiExpertProvider =
    require('../services/apiExpertProvider').apiExpertProvider;
  return { api, provider };
}

describe('outside a controlled test build', () => {
  it('fails closed on every read and write instead of reaching the network', async () => {
    const { api, provider } = load(false);

    await expect(provider.listExperts({})).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.getExpert('e1')).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.listConsultations({})).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.pending()).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.history()).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.getConsultation('c1')).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(
      provider.createConsultation({
        category: 'crop_disease',
        subject: 'Yellowing leaves',
        description: 'Leaves turning yellow on the paddy crop.',
      }),
    ).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.reply('c1', { body: 'hi' })).rejects.toThrow(
      'CONTROLLED_TEST_BUILD_REQUIRED',
    );
    await expect(
      provider.addAttachment('c1', { fileUrl: 'https://example.com/x.png' }),
    ).rejects.toThrow('CONTROLLED_TEST_BUILD_REQUIRED');
    await expect(provider.updateStatus('c1', 'resolved')).rejects.toThrow(
      'CONTROLLED_TEST_BUILD_REQUIRED',
    );

    expect(api.get).not.toHaveBeenCalled();
    expect(api.post).not.toHaveBeenCalled();
    expect(api.put).not.toHaveBeenCalled();
  });
});

describe('inside a controlled test build', () => {
  it('reaches the real experts endpoint', async () => {
    const { api, provider } = load(true);
    (api.get as jest.Mock).mockResolvedValue({
      items: [],
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 1,
    });

    await provider.listExperts({});

    expect(api.get).toHaveBeenCalledWith('/experts', expect.objectContaining({}));
  });
});
