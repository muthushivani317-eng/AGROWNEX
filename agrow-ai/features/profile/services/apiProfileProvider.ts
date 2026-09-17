import { useAuthStore } from '@/features/auth/store/authStore';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError } from '@/types';

import type {
  ApiFarmerLanguage,
  ApiFarmerMe,
  ApiFarmerPreferences,
  FarmerPreferences,
  FarmerProfile,
  FarmerProfileInput,
} from '../types';
import {
  apiToPreferences,
  apiToProfile,
  preferencesToApi,
  profileInputToApi,
  userToProfile,
} from './profileMapper';
import type { ProfileProvider } from './profileProvider';

/**
 * Talks to the AgrowAI backend (docs/API_CONTRACT.md → FARMER MODULE) through the
 * shared `api` client, which attaches the JWT, request id and language and
 * unwraps the response envelope. Used once a real backend is configured.
 */
export const apiProfileProvider: ProfileProvider = {
  async getProfile(): Promise<FarmerProfile> {
    try {
      // Read the profile and the language list; the flagged default language is
      // authoritative over the profile's own `language` field.
      const [me, languages] = await Promise.all([
        api.get<ApiFarmerMe>(endpoints.farmers.me),
        api.get<ApiFarmerLanguage[]>(endpoints.farmers.languages),
      ]);
      const preferred = languages.find((l) => l.is_default);
      return apiToProfile(preferred ? { ...me, language: preferred.language_code } : me);
    } catch (e) {
      // A 404 means the farmer hasn't completed their profile yet — a normal,
      // expected state, not a failure. Fall back to the current auth user so the
      // profile screen can render (and prompt them to complete it).
      if (e instanceof ApiError && e.status === 404) {
        const user = useAuthStore.getState().user;
        if (user) return userToProfile(user);
        // Defensive: this is an authenticated call, so a user should exist.
        return {
          fullName: '',
          language: 'ta',
          district: null,
          block: null,
          village: null,
          experienceYears: null,
          gender: null,
          education: null,
          preferredCrops: [],
          photoUrl: null,
          phone: null,
          email: null,
        };
      }
      // Genuine failures (network, 500, etc.) must still surface as errors.
      throw e;
    }
  },

  async updateProfile(input: FarmerProfileInput): Promise<FarmerProfile> {
    const me = await api.put<ApiFarmerMe>(
      endpoints.farmers.me,
      profileInputToApi(input),
    );
    // Keep the canonical language list in sync with the chosen language.
    await api.put<ApiFarmerLanguage[]>(endpoints.farmers.languages, {
      languages: [{ language_code: input.language, is_default: true }],
    });
    return apiToProfile(me);
  },

  async getPreferences(): Promise<FarmerPreferences> {
    const dto = await api.get<ApiFarmerPreferences>(endpoints.farmers.preferences);
    return apiToPreferences(dto);
  },

  async updatePreferences(
    patch: Partial<FarmerPreferences>,
  ): Promise<FarmerPreferences> {
    const dto = await api.put<ApiFarmerPreferences>(
      endpoints.farmers.preferences,
      preferencesToApi(patch),
    );
    return apiToPreferences(dto);
  },
};
