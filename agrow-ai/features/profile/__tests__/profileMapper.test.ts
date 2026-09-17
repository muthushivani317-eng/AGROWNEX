import type { AuthUser } from '@/features/auth/types';

import type { ApiFarmerMe, ApiFarmerPreferences, FarmerProfileInput } from '../types';
import {
  apiToPreferences,
  apiToProfile,
  preferencesToApi,
  profileInputToApi,
  profileInputToUserPatch,
  userToProfile,
} from '../services/profileMapper';

const user: AuthUser = {
  id: 'u1',
  phone: '+919876543210',
  name: 'Muthu Kumar',
  email: null,
  photoUrl: 'file:///photo.jpg',
  language: 'ta',
  district: 'madurai',
  block: 'Melur',
  village: 'Kottampatti',
  experienceYears: 12,
  gender: 'female',
  education: 'graduate',
  preferredCrops: ['paddy', 'sugarcane'],
  role: 'farmer',
  profileCompleted: true,
  createdAt: '2026-01-01T00:00:00.000Z',
};

describe('profileMapper', () => {
  it('maps an auth user to a profile', () => {
    const profile = userToProfile(user);
    expect(profile.fullName).toBe('Muthu Kumar');
    expect(profile.gender).toBe('female');
    expect(profile.education).toBe('graduate');
    expect(profile.preferredCrops).toEqual(['paddy', 'sugarcane']);
    expect(profile.phone).toBe('+919876543210');
    expect(profile.email).toBeNull();
  });

  it('maps a profile input to an auth-user patch (marks completed)', () => {
    const input: FarmerProfileInput = {
      fullName: 'Selvi R',
      language: 'en',
      district: 'thanjavur',
      block: null,
      village: null,
      experienceYears: 4,
      gender: 'male',
      education: 'secondary',
      preferredCrops: ['cotton'],
      photoUrl: null,
    };
    const patch = profileInputToUserPatch(input);
    expect(patch.name).toBe('Selvi R');
    expect(patch.language).toBe('en');
    expect(patch.gender).toBe('male');
    expect(patch.education).toBe('secondary');
    expect(patch.profileCompleted).toBe(true);
    expect(patch.preferredCrops).toEqual(['cotton']);
  });

  it('maps the backend /me envelope to a profile', () => {
    const dto: ApiFarmerMe = {
      id: 'p1',
      user_id: 'u1',
      full_name: 'Anitha',
      gender: 'female',
      language: 'ta',
      district: 'salem',
      block: null,
      village: null,
      profile_photo: 'https://cdn/x.jpg',
      experience_years: 6,
      education: 'primary',
      primary_crop: 'maize',
      secondary_crop: null,
      preferred_crops: ['maize'],
      phone_number: '+910000000000',
      email: 'a@b.com',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };
    const profile = apiToProfile(dto);
    expect(profile.fullName).toBe('Anitha');
    expect(profile.photoUrl).toBe('https://cdn/x.jpg');
    expect(profile.gender).toBe('female');
    expect(profile.education).toBe('primary');
    expect(profile.preferredCrops).toEqual(['maize']);
    expect(profile.email).toBe('a@b.com');
  });

  it('maps a profile input to the backend update payload (snake_case)', () => {
    const input: FarmerProfileInput = {
      fullName: 'Kumar S',
      language: 'ta',
      district: 'erode',
      block: 'Bhavani',
      village: null,
      experienceYears: null,
      gender: null,
      education: null,
      preferredCrops: ['banana', 'coconut'],
      photoUrl: null,
    };
    const payload = profileInputToApi(input);
    expect(payload).toEqual({
      full_name: 'Kumar S',
      gender: null,
      language: 'ta',
      district: 'erode',
      block: 'Bhavani',
      village: null,
      experience_years: null,
      education: null,
      profile_photo: null,
      preferred_crops: ['banana', 'coconut'],
    });
  });

  it('maps preferences both ways and only sends defined patch keys', () => {
    const dto: ApiFarmerPreferences = {
      id: 'pref1',
      farmer_id: 'p1',
      theme: 'dark',
      notifications_enabled: false,
      voice_enabled: true,
      preferred_units: 'imperial',
      default_crop: 'paddy',
    };
    const prefs = apiToPreferences(dto);
    expect(prefs.theme).toBe('dark');
    expect(prefs.notificationsEnabled).toBe(false);
    expect(prefs.preferredUnits).toBe('imperial');

    expect(preferencesToApi({ voiceEnabled: false })).toEqual({ voice_enabled: false });
    expect(preferencesToApi({})).toEqual({});
  });
});
