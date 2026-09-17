jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import { ExpertError, type ExpertProvider } from '../services/expertProvider';
import {
  consultationOutbox,
  isOfflineError,
  syncConsultations,
} from '../services/expertSync';

const networkError = () =>
  new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

function fakeProvider(overrides: Partial<ExpertProvider> = {}): ExpertProvider {
  return {
    listExperts: jest.fn(),
    getExpert: jest.fn(),
    listConsultations: jest.fn(),
    pending: jest.fn(),
    history: jest.fn(),
    getConsultation: jest.fn(),
    createConsultation: jest.fn(),
    reply: jest.fn().mockResolvedValue(undefined),
    addAttachment: jest.fn().mockResolvedValue(undefined),
    updateStatus: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  } as ExpertProvider;
}

describe('expertSync', () => {
  beforeEach(() => consultationOutbox.clear());

  it('detects offline errors', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new ExpertError('network', 'x'))).toBe(true);
    expect(isOfflineError(new ExpertError('consultation_closed', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('drains queued reply/attachment/status actions on reconnect', async () => {
    consultationOutbox.enqueue({ op: 'reply', consultationId: 'c1', reply: { body: 'hi' } });
    consultationOutbox.enqueue({
      op: 'attachment',
      consultationId: 'c1',
      attachment: { fileUrl: 'https://r2/a.jpg' },
    });
    consultationOutbox.enqueue({ op: 'status', consultationId: 'c1', status: 'resolved' });
    expect(consultationOutbox.count()).toBe(3);

    const provider = fakeProvider();
    const result = await syncConsultations(provider);
    expect(result.synced).toBe(3);
    expect(result.remaining).toBe(0);
    expect(provider.reply).toHaveBeenCalledWith('c1', { body: 'hi' });
    expect(provider.updateStatus).toHaveBeenCalledWith('c1', 'resolved', undefined);
  });

  it('keeps the queue intact while still offline', async () => {
    consultationOutbox.enqueue({ op: 'reply', consultationId: 'c1', reply: { body: 'hi' } });
    const provider = fakeProvider({
      reply: jest.fn().mockRejectedValue(networkError()),
    });
    const result = await syncConsultations(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1);
  });

  it('drops a poison entry on a non-network rejection', async () => {
    consultationOutbox.enqueue({ op: 'status', consultationId: 'c1', status: 'resolved' });
    const provider = fakeProvider({
      updateStatus: jest.fn().mockRejectedValue(new ExpertError('bad', 'x')),
    });
    const result = await syncConsultations(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });
});
