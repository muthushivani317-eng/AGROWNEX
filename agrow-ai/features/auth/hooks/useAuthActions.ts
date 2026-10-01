import { useMutation } from '@tanstack/react-query';

import { getLanguage } from '@/localization';
import { offlineQueue } from '@/lib/db';
import { logger } from '@/lib/logger';
import { queryClient } from '@/lib/queryClient';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type SupportedLanguage } from '@/types';
import { uuid } from '@/utils/id';
import type { ApiFarmerMeUpdate } from '@/features/profile/types';

import type { CompleteProfileData } from '../schemas';
import { normalizeIndianPhone } from '../phone';
import { authProvider } from '../services/authProvider';
import { useAuthStore } from '../store/authStore';
import { useOtpFlowStore } from '../store/otpFlowStore';
import { AuthError } from '../types';

/** Request an OTP for the given 10-digit number and open the verify flow. */
export function useSendOtp() {
  const start = useOtpFlowStore((s) => s.start);
  const reset = useOtpFlowStore((s) => s.reset);

  return useMutation({
    mutationFn: async (phone10: string) => {
      const phoneE164 = normalizeIndianPhone(phone10);
      const language = getLanguage() as SupportedLanguage;
      const confirmation = await authProvider.sendOtp(phoneE164);
      return { phoneE164, phone10, language, confirmation };
    },
    onMutate: () => reset(),
    onSuccess: ({ phoneE164, phone10, language, confirmation }) => {
      start({
        phoneE164,
        displayPhone: `+91 ${phone10.slice(0, 5)} ${phone10.slice(5)}`,
        language,
        confirmation,
      });
    },
  });
}

/** Resend the OTP for the number already in the flow. */
export function useResendOtp() {
  const beginConfirmationRequest = useOtpFlowStore((s) => s.beginConfirmationRequest);
  const setConfirmationIfCurrent = useOtpFlowStore((s) => s.setConfirmationIfCurrent);

  return useMutation({
    mutationFn: async () => {
      const request = beginConfirmationRequest();
      if (!request) throw new AuthError('auth/no-flow', 'No number in progress');
      const confirmation = await authProvider.sendOtp(request.phoneE164);
      const installed = setConfirmationIfCurrent({
        confirmation,
        expectedGeneration: request.generation,
        expectedPhone: request.phoneE164,
      });
      logger.info(
        'auth.otpFlow',
        installed ? 'resend_confirmation_installed' : 'stale_resend_discarded',
      );
      return { installed };
    },
  });
}

let confirmInFlight = false;

/** Confirm the entered OTP and establish a session. */
export function useVerifyOtp() {
  const signIn = useAuthStore((s) => s.signIn);
  const reset = useOtpFlowStore((s) => s.reset);

  return useMutation({
    mutationFn: async (code: string) => {
      if (confirmInFlight) {
        throw new AuthError('auth/in-flight', 'auth.otpConfirmFailed');
      }
      confirmInFlight = true;
      try {
        const { confirmation, language, generation } = useOtpFlowStore.getState();
        if (!confirmation) throw new AuthError('auth/no-flow', 'auth.otpConfirmFailed');
        let credential;
        try {
          credential = await confirmation.confirm(code);
        } catch (error) {
          if (
            error instanceof AuthError &&
            (error.code === 'auth/session-expired' || error.code === 'auth/code-expired')
          ) {
            useOtpFlowStore.getState().invalidateConfirmation(generation);
            logger.info('auth.otpFlow', 'expired_confirmation_invalidated');
          }
          throw error;
        }
        const currentFlow = useOtpFlowStore.getState();
        if (
          currentFlow.generation !== generation ||
          currentFlow.confirmation !== confirmation
        ) {
          await authProvider.signOut().catch(() => {});
          logger.info('auth.otpFlow', 'stale_confirmation_rejected');
          throw new AuthError('auth/session-expired', 'auth.otpCodeExpired');
        }
        await signIn(credential, language);
        return credential;
      } finally {
        confirmInFlight = false;
      }
    },
    onSuccess: () => reset(),
  });
}

/**
 * Persist the completed farmer profile to the backend (PUT /farmers/me), then
 * mirror it into the local auth store. This reuses the same endpoint and
 * offline-outbox pattern as the Edit Profile flow
 * (features/profile/hooks/useProfile.ts → useUpdateProfile;
 * docs/FRONTEND_ARCHITECTURE.md → OFFLINE STRATEGY).
 *
 * Previously this only wrote to local device storage via `updateUser` and
 * never called the backend at all, so a farmer's onboarding data (name,
 * district, crops, etc.) was silently lost on reinstall or a second device
 * (see farmer-release-readiness audit, 2026-08-18).
 */
/** Saved values the onboarding form does not edit but must not wipe (Edit profile). */
export interface PreservedProfileFields {
  gender?: string | null;
  education?: string | null;
}

export function useCompleteProfile() {
  const updateUser = useAuthStore((s) => s.updateUser);

  return useMutation({
    mutationFn: async ({ preserve, ...data }: CompleteProfileData & { preserve?: PreservedProfileFields }) => {
      const payload: ApiFarmerMeUpdate = {
        full_name: data.name,
        gender: preserve?.gender ?? null,
        language: data.language,
        district: data.district,
        block: data.block || null,
        village: data.village || null,
        experience_years: data.experienceYears,
        education: preserve?.education ?? null,
        profile_photo: data.photoUrl,
        preferred_crops: data.preferredCrops,
        land_holding_acres: data.landHoldingAcres,
        farmer_type: data.farmerType,
        landmark: data.landmark || null,
        latitude: data.latitude,
        longitude: data.longitude,
        farm_products: data.farmProducts.map((product) => ({
          product_id: product.productId,
          category: product.category,
          expected_harvest_month: product.expectedHarvestMonth,
          approximate_quantity: product.approximateQuantity,
          unit: product.unit,
          available_for_sale: product.availableForSale,
        })),
        wants_fpo_support: data.wantsFpoSupport,
        wants_kvk_support: data.wantsKvkSupport,
      };

      try {
        await api.put(endpoints.farmers.me, payload);
      } catch (e) {
        if (e instanceof ApiError && e.isNetwork) {
          // No connection right now: queue the write so it syncs once the
          // farmer is back online, instead of losing what they just entered.
          await offlineQueue.enqueue({
            id: uuid(),
            endpoint: endpoints.farmers.me,
            method: 'PUT',
            payload,
            entityType: 'farmer_profile',
          });
        } else {
          // A genuine validation/server error — surface it rather than
          // silently marking onboarding complete with unsaved data.
          throw e;
        }
      }

      await updateUser({
        name: data.name,
        language: data.language,
        district: data.district,
        block: data.block || null,
        village: data.village || null,
        experienceYears: data.experienceYears,
        preferredCrops: data.preferredCrops,
        photoUrl: data.photoUrl,
        profileCompleted: true,
      });
    },
    // Profile tab, Edit profile and Account settings read cached copies; a
    // missing invalidation left them showing "Set up your profile" (the
    // pre-onboarding 404) until the app restarted.
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['profile'] });
      void queryClient.invalidateQueries({ queryKey: ['partnerLinks'] });
    },
  });
}

/** Sign out and clear all cached data. */
export function useLogout() {
  const storeSignOut = useAuthStore((s) => s.signOut);

  return useMutation({
    mutationFn: async () => {
      await authProvider.signOut().catch(() => {});
      await storeSignOut();
      queryClient.clear();
    },
  });
}

/** Close the backend account, then remove all local and Firebase credentials. */
export function useCloseAccount() {
  const storeSignOut = useAuthStore((s) => s.signOut);

  return useMutation({
    mutationFn: async () => {
      await api.delete<void>(endpoints.auth.account);
      await authProvider.signOut().catch(() => {});
      await storeSignOut();
      queryClient.clear();
    },
  });
}
