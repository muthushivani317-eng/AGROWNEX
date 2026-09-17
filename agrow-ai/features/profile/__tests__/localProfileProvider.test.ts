// Avoid pulling i18next side effects into the store when updateUser runs.
jest.mock('@/localization', () => ({
  setLanguage: jest.fn(() => Promise.resolve()),
  getLanguage: () => 'ta',
}));

import { useAuthStore } from '@/features/auth/store/authStore';
import type { AuthUser } from '@/features/auth/types';
import { appStorage } from '@/lib/storage';

import { PREFERENCES_STORAGE_KEY } from '../constants';
import { localProfileProvider } from '../services/localProfileProvider';

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
  profileCompleted: true,
  createdAt: '2026-01-01T00:00:00.000Z',
};

describe('localProfileProvider', () => {
  beforeEach(() => {
    appStorage.remove(PREFERENCES_STORAGE_KEY);
    useAuthStore.setState({ status: 'authenticated', user: { ...baseUser }, tokens: null });
  });

  it('reads the profile from the auth store', async () => {
    const profile = await localProfileProvider.getProfile();
    expect(profile.fullName).toBe('Muthu Kumar');
    expect(profile.district).toBe('madurai');
    expect(profile.preferredCrops).toEqual(['paddy']);
    expect(profile.phone).toBe('+919876543210');
  });

  it('persists profile edits back to the auth store', async () => {
    const saved = await localProfileProvider.updateProfile({
      fullName: 'Muthu K',
      language: 'en',
      district: 'thanjavur',
      block: null,
      village: 'Pillaiyarpatti',
      experienceYears: 15,
      gender: 'male',
      education: 'graduate',
      preferredCrops: ['cotton', 'maize'],
      photoUrl: 'file:///new.jpg',
    });

    expect(saved.fullName).toBe('Muthu K');
    const user = useAuthStore.getState().user;
    expect(user?.name).toBe('Muthu K');
    expect(user?.village).toBe('Pillaiyarpatti');
    expect(user?.gender).toBe('male');
    expect(user?.education).toBe('graduate');
    expect(user?.preferredCrops).toEqual(['cotton', 'maize']);
    expect(user?.profileCompleted).toBe(true);
  });

  it('returns default preferences then persists updates', async () => {
    const defaults = await localProfileProvider.getPreferences();
    expect(defaults.notificationsEnabled).toBe(true);
    expect(defaults.preferredUnits).toBe('metric');

    const updated = await localProfileProvider.updatePreferences({
      notificationsEnabled: false,
      preferredUnits: 'imperial',
    });
    expect(updated.notificationsEnabled).toBe(false);
    expect(updated.preferredUnits).toBe('imperial');
    expect(updated.voiceEnabled).toBe(true); // untouched

    // Persisted across reads.
    const again = await localProfileProvider.getPreferences();
    expect(again.notificationsEnabled).toBe(false);
    expect(again.preferredUnits).toBe('imperial');
  });
});
