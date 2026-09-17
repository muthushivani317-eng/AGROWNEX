import type { SupportedLanguage } from '@/types';

import type { FarmerPreferences, ThemePreference, UnitPreference } from './types';

/** Preferred-language options (Tamil first — docs/PRODUCT_RULES.md). */
export const LANGUAGE_OPTIONS: { value: SupportedLanguage; label: string }[] = [
  { value: 'ta', label: 'தமிழ்' },
  { value: 'en', label: 'English' },
];

/** Measurement-unit options; label is an i18n key under `profile`. */
export const UNIT_OPTIONS: { value: UnitPreference; labelKey: string }[] = [
  { value: 'metric', labelKey: 'profile.unitMetric' },
  { value: 'imperial', labelKey: 'profile.unitImperial' },
];

/** Gender options (optional field); label is an i18n key under `profile`. */
export const GENDER_SELECT_OPTIONS: { value: string; labelKey: string }[] = [
  { value: 'male', labelKey: 'profile.genderMale' },
  { value: 'female', labelKey: 'profile.genderFemale' },
  { value: 'other', labelKey: 'profile.genderOther' },
];

/** Education-level options (optional field); label is an i18n key under `profile`. */
export const EDUCATION_SELECT_OPTIONS: { value: string; labelKey: string }[] = [
  { value: 'none', labelKey: 'profile.educationNone' },
  { value: 'primary', labelKey: 'profile.educationPrimary' },
  { value: 'secondary', labelKey: 'profile.educationSecondary' },
  { value: 'higher_secondary', labelKey: 'profile.educationHigherSecondary' },
  { value: 'graduate', labelKey: 'profile.educationGraduate' },
];

export const THEME_VALUES: ThemePreference[] = ['system', 'light', 'dark'];

/** Defaults mirror the backend farmer_preferences server defaults. */
export const DEFAULT_PREFERENCES: FarmerPreferences = {
  theme: 'system',
  notificationsEnabled: true,
  voiceEnabled: true,
  preferredUnits: 'metric',
  defaultCrop: null,
};

/** MMKV key for locally-persisted preferences (local provider only). */
export const PREFERENCES_STORAGE_KEY = 'agrowai.profile.preferences';

/** React Query keys for profile server state. */
export const profileKeys = {
  me: ['profile', 'me'] as const,
  preferences: ['profile', 'preferences'] as const,
};
