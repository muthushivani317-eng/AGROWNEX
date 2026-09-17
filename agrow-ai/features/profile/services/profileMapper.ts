import type { AuthUser } from '@/features/auth/types';
import type { SupportedLanguage } from '@/types';

import type {
  ApiFarmerMe,
  ApiFarmerMeUpdate,
  ApiFarmerPreferences,
  FarmerPreferences,
  FarmerProfile,
  FarmerProfileInput,
  ThemePreference,
} from '../types';

/**
 * Pure translations between the client models (AuthUser / API envelopes) and the
 * profile domain types. Kept side-effect free so they are trivially unit-tested.
 */

export function userToProfile(user: AuthUser): FarmerProfile {
  return {
    fullName: user.name ?? '',
    language: user.language,
    district: user.district,
    block: user.block,
    village: user.village,
    experienceYears: user.experienceYears,
    gender: user.gender,
    education: user.education,
    preferredCrops: user.preferredCrops ?? [],
    photoUrl: user.photoUrl,
    phone: user.phone,
    email: user.email,
  };
}

export function profileInputToUserPatch(input: FarmerProfileInput): Partial<AuthUser> {
  return {
    name: input.fullName,
    language: input.language,
    district: input.district,
    block: input.block,
    village: input.village,
    experienceYears: input.experienceYears,
    gender: input.gender ?? null,
    education: input.education ?? null,
    preferredCrops: input.preferredCrops,
    photoUrl: input.photoUrl,
    profileCompleted: true,
  };
}

export function apiToProfile(dto: ApiFarmerMe): FarmerProfile {
  return {
    fullName: dto.full_name ?? '',
    language: (dto.language as SupportedLanguage) ?? 'ta',
    district: dto.district,
    block: dto.block,
    village: dto.village,
    experienceYears: dto.experience_years,
    gender: dto.gender,
    education: dto.education,
    preferredCrops: dto.preferred_crops ?? [],
    photoUrl: dto.profile_photo,
    phone: dto.phone_number,
    email: dto.email,
  };
}

export function profileInputToApi(input: FarmerProfileInput): ApiFarmerMeUpdate {
  return {
    full_name: input.fullName,
    gender: input.gender ?? null,
    language: input.language,
    district: input.district,
    block: input.block,
    village: input.village,
    experience_years: input.experienceYears,
    education: input.education ?? null,
    profile_photo: input.photoUrl,
    preferred_crops: input.preferredCrops,
  };
}

export function apiToPreferences(dto: ApiFarmerPreferences): FarmerPreferences {
  return {
    theme: normaliseTheme(dto.theme),
    notificationsEnabled: dto.notifications_enabled,
    voiceEnabled: dto.voice_enabled,
    preferredUnits: dto.preferred_units === 'imperial' ? 'imperial' : 'metric',
    defaultCrop: dto.default_crop,
  };
}

/** Camel→snake for a partial preferences patch (only defined keys are sent). */
export function preferencesToApi(
  patch: Partial<FarmerPreferences>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (patch.theme !== undefined) out.theme = patch.theme;
  if (patch.notificationsEnabled !== undefined)
    out.notifications_enabled = patch.notificationsEnabled;
  if (patch.voiceEnabled !== undefined) out.voice_enabled = patch.voiceEnabled;
  if (patch.preferredUnits !== undefined) out.preferred_units = patch.preferredUnits;
  if (patch.defaultCrop !== undefined) out.default_crop = patch.defaultCrop;
  return out;
}

function normaliseTheme(value: string): ThemePreference {
  return value === 'light' || value === 'dark' ? value : 'system';
}
