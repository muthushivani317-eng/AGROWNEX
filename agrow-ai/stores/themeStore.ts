import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { mmkvZustandStorage, StorageKeys } from '@/lib/storage';

export type ThemePreference = 'system' | 'light' | 'dark';

interface ThemeState {
  preference: ThemePreference;
  sunlightEnabled: boolean;
  hydrated: boolean;
  setPreference: (pref: ThemePreference) => void;
  setSunlightEnabled: (enabled: boolean) => void;
  setHydrated: () => void;
}

/** Global theme preference (client state → Zustand, persisted in MMKV). */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      preference: 'system',
      sunlightEnabled: false,
      hydrated: false,
      setPreference: (preference) => set({ preference }),
      setSunlightEnabled: (sunlightEnabled) => set({ sunlightEnabled }),
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: StorageKeys.themePref,
      storage: createJSONStorage(() => mmkvZustandStorage),
      partialize: (s) => ({
        preference: s.preference,
        sunlightEnabled: s.sunlightEnabled,
      }),
      onRehydrateStorage: () => (state) => state?.setHydrated(),
    },
  ),
);
