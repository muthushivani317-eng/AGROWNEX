import * as ImagePicker from 'expo-image-picker';

import { logger } from '@/lib/logger';

/**
 * Launch the gallery to pick a square profile photo. Returns the local URI, or
 * null if the user cancels or denies permission. Upload to S3 happens in a later
 * phase; for now the local URI is stored on the profile.
 */
export async function pickProfileImage(): Promise<string | null> {
  try {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return null;

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });

    if (result.canceled || !result.assets.length) return null;
    return result.assets[0].uri;
  } catch (e) {
    logger.warn('pickProfileImage', e);
    return null;
  }
}

/**
 * Launch the gallery to pick a general (non-square) photo — used for produce
 * harvest photos. Returns the local URI, or null if cancelled/denied.
 */
export async function pickPhoto(): Promise<string | null> {
  try {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return null;

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.7,
    });

    if (result.canceled || !result.assets.length) return null;
    return result.assets[0].uri;
  } catch (e) {
    logger.warn('pickPhoto', e);
    return null;
  }
}

/**
 * Launch the camera to capture a general (non-square) photo — the camera
 * counterpart to `pickPhoto` (used for produce/soil forms, which previously
 * could only open the gallery; found in the 2026-08 pre-release audit).
 * Returns the local URI, or null if cancelled/denied.
 */
export async function capturePhoto(): Promise<string | null> {
  try {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return null;

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.7,
    });

    if (result.canceled || !result.assets.length) return null;
    return result.assets[0].uri;
  } catch (e) {
    logger.warn('capturePhoto', e);
    return null;
  }
}
