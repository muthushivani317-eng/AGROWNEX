import { useOtpFlowStore } from '../store/otpFlowStore';
import type { OtpConfirmation } from '../types';

const confirmation = (phone: string): OtpConfirmation => ({
  phone,
  confirm: jest.fn(),
});

describe('otpFlowStore confirmation generations', () => {
  beforeEach(() => useOtpFlowStore.getState().reset());

  it('invalidates an expired confirmation without losing the resend phone', () => {
    useOtpFlowStore.getState().start({
      phoneE164: '+919876543210',
      displayPhone: '+91 98765 43210',
      language: 'en',
      confirmation: confirmation('+919876543210'),
    });
    const generation = useOtpFlowStore.getState().generation;

    useOtpFlowStore.getState().invalidateConfirmation(generation);

    expect(useOtpFlowStore.getState().confirmation).toBeNull();
    expect(useOtpFlowStore.getState().phoneE164).toBe('+919876543210');
  });

  it('does not let an older failed attempt invalidate the newest resend', () => {
    useOtpFlowStore.getState().start({
      phoneE164: '+919876543210',
      displayPhone: '+91 98765 43210',
      language: 'en',
      confirmation: confirmation('+919876543210'),
    });
    const oldGeneration = useOtpFlowStore.getState().generation;
    const newest = confirmation('+919876543210');
    useOtpFlowStore.getState().setConfirmation(newest);

    useOtpFlowStore.getState().invalidateConfirmation(oldGeneration);

    expect(useOtpFlowStore.getState().confirmation).toBe(newest);
    expect(useOtpFlowStore.getState().generation).toBe(oldGeneration + 1);
  });

  it('discards a delayed resend after the user starts a newer phone flow', () => {
    useOtpFlowStore.getState().start({
      phoneE164: '+919111111111',
      displayPhone: '+91 91111 11111',
      language: 'en',
      confirmation: confirmation('+919111111111'),
    });
    const oldGeneration = useOtpFlowStore.getState().generation;

    const newest = confirmation('+919222222222');
    useOtpFlowStore.getState().start({
      phoneE164: '+919222222222',
      displayPhone: '+91 92222 22222',
      language: 'en',
      confirmation: newest,
    });
    const installed = useOtpFlowStore.getState().setConfirmationIfCurrent({
      expectedGeneration: oldGeneration,
      expectedPhone: '+919111111111',
      confirmation: confirmation('+919111111111'),
    });

    expect(installed).toBe(false);
    expect(useOtpFlowStore.getState().phoneE164).toBe('+919222222222');
    expect(useOtpFlowStore.getState().confirmation).toBe(newest);
  });

  it('makes the later-started resend win when two responses finish out of order', () => {
    useOtpFlowStore.getState().start({
      phoneE164: '+919876543210',
      displayPhone: '+91 98765 43210',
      language: 'en',
      confirmation: confirmation('+919876543210'),
    });

    const olderRequest = useOtpFlowStore.getState().beginConfirmationRequest();
    const newerRequest = useOtpFlowStore.getState().beginConfirmationRequest();
    expect(olderRequest).not.toBeNull();
    expect(newerRequest).not.toBeNull();
    expect(newerRequest!.generation).toBe(olderRequest!.generation + 1);

    const olderResult = confirmation('+919876543210');
    const newerResult = confirmation('+919876543210');
    const olderInstalled = useOtpFlowStore.getState().setConfirmationIfCurrent({
      expectedGeneration: olderRequest!.generation,
      expectedPhone: olderRequest!.phoneE164,
      confirmation: olderResult,
    });
    const newerInstalled = useOtpFlowStore.getState().setConfirmationIfCurrent({
      expectedGeneration: newerRequest!.generation,
      expectedPhone: newerRequest!.phoneE164,
      confirmation: newerResult,
    });

    expect(olderInstalled).toBe(false);
    expect(newerInstalled).toBe(true);
    expect(useOtpFlowStore.getState().confirmation).toBe(newerResult);
  });
});
