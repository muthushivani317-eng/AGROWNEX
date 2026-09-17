import { create } from 'zustand';

import type { SupportedLanguage } from '@/types';

import type { OtpConfirmation } from '../types';

/**
 * Ephemeral (non-persisted) state for the in-progress OTP flow, shared between
 * the login and verify screens. Cleared once verification completes or is
 * abandoned so a stale confirmation handle is never reused.
 */
interface OtpFlowState {
  phoneE164: string | null;
  displayPhone: string | null;
  language: SupportedLanguage;
  confirmation: OtpConfirmation | null;
  /** Monotonic request generation used to reject stale confirmation handles. */
  generation: number;
  start: (args: {
    phoneE164: string;
    displayPhone: string;
    language: SupportedLanguage;
    confirmation: OtpConfirmation;
  }) => void;
  setConfirmation: (confirmation: OtpConfirmation) => void;
  beginConfirmationRequest: () => {
    generation: number;
    phoneE164: string;
  } | null;
  setConfirmationIfCurrent: (args: {
    expectedGeneration: number;
    expectedPhone: string;
    confirmation: OtpConfirmation;
  }) => boolean;
  invalidateConfirmation: (expectedGeneration: number) => void;
  reset: () => void;
}

export const useOtpFlowStore = create<OtpFlowState>((set) => ({
  phoneE164: null,
  displayPhone: null,
  language: 'ta',
  confirmation: null,
  generation: 0,
  start: ({ phoneE164, displayPhone, language, confirmation }) =>
    set((state) => ({
      phoneE164,
      displayPhone,
      language,
      confirmation,
      generation: state.generation + 1,
    })),
  setConfirmation: (confirmation) =>
    set((state) => ({ confirmation, generation: state.generation + 1 })),
  beginConfirmationRequest: () => {
    let request: { generation: number; phoneE164: string } | null = null;
    set((state) => {
      if (!state.phoneE164) return {};
      const generation = state.generation + 1;
      request = { generation, phoneE164: state.phoneE164 };
      // Reserving the generation before the network call ensures a later
      // resend always supersedes an earlier one, irrespective of response order.
      return { generation, confirmation: null };
    });
    return request;
  },
  setConfirmationIfCurrent: ({ expectedGeneration, expectedPhone, confirmation }) => {
    let installed = false;
    set((state) => {
      if (
        state.generation !== expectedGeneration ||
        state.phoneE164 !== expectedPhone
      ) {
        return {};
      }
      installed = true;
      return { confirmation, generation: state.generation + 1 };
    });
    return installed;
  },
  invalidateConfirmation: (expectedGeneration) =>
    set((state) =>
      state.generation === expectedGeneration ? { confirmation: null } : {},
    ),
  reset: () =>
    set((state) => ({
      phoneE164: null,
      displayPhone: null,
      confirmation: null,
      generation: state.generation + 1,
    })),
}));
