import { useAuthStore } from '@/features/auth/store/authStore';
import { appStorage } from '@/lib/storage';

import { DEFAULT_PREFERENCES, PREFERENCES_STORAGE_KEY } from '../constants';
import type { FarmerPreferences, FarmerProfile, FarmerProfileInput } from '../types';
import { profileInputToUserPatch, userToProfile } from './profileMapper';
import { ProfileError, type ProfileProvider } from './profileProvider';

/**
 * Offline-first provider used until a real backend/Firebase is configured. The
 * profile lives in the auth store (persisted to encrypted MMKV) — the same
 * source of truth the rest of the app reads — and preferences live in app MMKV.
 * No network is involved, so reads/writes always succeed on-device.
 */
function readPreferences(): FarmerPreferences {
  return appStorage.getJSON<FarmerPreferences>(PREFERENCES_STORAGE_KEY) ?? {
    ...DEFAULT_PREFERENCES,
  };
}

export const localProfileProvider: ProfileProvider = {
  async getProfile(): Promise<FarmerProfile> {
    const user = useAuthStore.getState().user;
    if (!user) throw new ProfileError('no_session', 'No authenticated user');
    return userToProfile(user);
  },

  async updateProfile(input: FarmerProfileInput): Promise<FarmerProfile> {
    await useAuthStore.getState().updateUser(profileInputToUserPatch(input));
    const user = useAuthStore.getState().user;
    if (!user) throw new ProfileError('no_session', 'No authenticated user');
    return userToProfile(user);
  },

  async getPreferences(): Promise<FarmerPreferences> {
    return readPreferences();
  },

  async updatePreferences(
    patch: Partial<FarmerPreferences>,
  ): Promise<FarmerPreferences> {
    const next = { ...readPreferences(), ...patch };
    appStorage.setJSON(PREFERENCES_STORAGE_KEY, next);
    return next;
  },
};
