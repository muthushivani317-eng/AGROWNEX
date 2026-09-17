// Avoid pulling i18next side effects into the store when it initialises.
jest.mock('@/localization', () => ({
  setLanguage: jest.fn(() => Promise.resolve()),
  getLanguage: () => 'ta',
}));

// Control the HTTP client so getProfile()'s error handling can be exercised.
// `configureApiAuth` is a no-op here — the auth store calls it at module load.
jest.mock('@/services/apiClient', () => ({
  api: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
  configureApiAuth: jest.fn(),
}));

import { useAuthStore } from '@/features/auth/store/authStore';
import type { AuthUser } from '@/features/auth/types';
import { api } from '@/services/apiClient';
import { ApiError } from '@/types';

import { apiProfileProvider } from '../services/apiProfileProvider';
import { userToProfile } from '../services/profileMapper';

const apiGet = api.get as jest.Mock;

const baseUser: AuthUser = {
  id: 'u1',
  farmerRef: null,
  phone: '+919876543210',
  name: 'Muthu Kumar',
  email: null,
  photoUrl: null,
  language: 'ta',
  district: 'madurai',
  block: 'Melur',
  village: null,
  experienceYears: 12,
  gender: 'female',
  education: 'secondary',
  preferredCrops: ['paddy'],
  role: 'farmer',
  profileCompleted: false,
  createdAt: '2026-01-01T00:00:00.000Z',
};

function apiError(status: number): ApiError {
  return new ApiError({ status, message: `err ${status}`, errorCode: 'test_error' });
}

describe('apiProfileProvider.getProfile', () => {
  beforeEach(() => {
    apiGet.mockReset();
    useAuthStore.setState({ status: 'authenticated', user: { ...baseUser }, tokens: null });
  });

  it('falls back to the auth-store user when the profile is not found (404)', async () => {
    apiGet.mockRejectedValue(apiError(404));

    const profile = await apiProfileProvider.getProfile();

    expect(profile).toEqual(userToProfile(baseUser));
  });

  it('returns a default empty profile when there is no auth user (404)', async () => {
    apiGet.mockRejectedValue(apiError(404));
    useAuthStore.setState({ user: null });

    const profile = await apiProfileProvider.getProfile();

    expect(profile).toEqual({
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
    });
  });

  it('rethrows a non-404 ApiError (e.g. 500) instead of swallowing it', async () => {
    const err = apiError(500);
    apiGet.mockRejectedValue(err);

    await expect(apiProfileProvider.getProfile()).rejects.toBe(err);
  });

  it('rethrows a network error instead of swallowing it', async () => {
    const err = new Error('Network request failed');
    apiGet.mockRejectedValue(err);

    await expect(apiProfileProvider.getProfile()).rejects.toBe(err);
  });
});
