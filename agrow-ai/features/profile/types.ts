import type { SupportedLanguage } from '@/types';

/**
 * Farmer Profile domain types (docs/API_CONTRACT.md → FARMER MODULE).
 * Client-side camelCase mirror of the backend farmer schemas.
 */

export type ThemePreference = 'system' | 'light' | 'dark';
export type UnitPreference = 'metric' | 'imperial';

/** Editable profile fields (what the Edit Profile form produces). */
export interface FarmerProfileInput {
  fullName: string;
  language: SupportedLanguage;
  district: string | null;
  block: string | null;
  village: string | null;
  experienceYears: number | null;
  gender?: string | null;
  education?: string | null;
  preferredCrops: string[];
  photoUrl: string | null;
}

/** Full profile as shown on the View screen (adds read-only contact details). */
export interface FarmerProfile extends FarmerProfileInput {
  phone: string | null;
  email: string | null;
}

/** App preferences (docs/DATABASE_SCHEMA.md → farmer_preferences). */
export interface FarmerPreferences {
  theme: ThemePreference;
  notificationsEnabled: boolean;
  voiceEnabled: boolean;
  preferredUnits: UnitPreference;
  defaultCrop: string | null;
}

// --- Backend envelope shapes (snake_case), used only by the API provider. --- //
export interface ApiFarmerMe {
  id: string;
  user_id: string;
  full_name: string | null;
  gender: string | null;
  language: string;
  district: string | null;
  block: string | null;
  village: string | null;
  profile_photo: string | null;
  experience_years: number | null;
  education: string | null;
  primary_crop: string | null;
  secondary_crop: string | null;
  preferred_crops: string[];
  phone_number: string | null;
  email: string | null;
  land_holding_acres?: number | null;
  farmer_type?: string | null;
  landmark?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  farm_products?: ApiFarmProduct[];
  wants_fpo_support?: boolean;
  wants_kvk_support?: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiFarmerMeUpdate {
  full_name: string;
  gender: string | null;
  language: string;
  district: string | null;
  block: string | null;
  village: string | null;
  experience_years: number | null;
  education: string | null;
  profile_photo: string | null;
  preferred_crops: string[];
  land_holding_acres?: number | null;
  farmer_type?: string | null;
  landmark?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  farm_products?: ApiFarmProduct[];
  wants_fpo_support?: boolean;
  wants_kvk_support?: boolean;
}

export interface ApiFarmProduct {
  product_id: string;
  category: string;
  expected_harvest_month: string | null;
  approximate_quantity: number | null;
  unit: 'kg' | 'quintal' | 'tonne' | 'bag' | 'count' | 'litre';
  available_for_sale: boolean;
}

export interface ApiFarmerPreferences {
  id: string;
  farmer_id: string;
  theme: string;
  notifications_enabled: boolean;
  voice_enabled: boolean;
  preferred_units: string;
  default_crop: string | null;
}

export interface ApiFarmerLanguage {
  id: string;
  farmer_id: string;
  language_code: string;
  is_default: boolean;
}
