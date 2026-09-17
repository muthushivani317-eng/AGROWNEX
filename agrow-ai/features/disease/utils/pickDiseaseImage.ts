import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import {
  EncodingType,
  getInfoAsync,
  readAsStringAsync,
} from 'expo-file-system/legacy';
import i18next from 'i18next';
import { Alert } from 'react-native';

import { logger } from '@/lib/logger';

import type { PickedImage } from '../types';

/** Capture (camera) or choose (gallery) without moving image bytes onto the JS thread. */
function inferMime(uri: string, assetMime?: string | null): string {
  if (assetMime) return assetMime;
  const ext = uri.split('.').pop()?.toLowerCase();
  if (ext === 'png') return 'image/png';
  if (ext === 'webp') return 'image/webp';
  return 'image/jpeg';
}

function toPicked(
  asset: ImagePicker.ImagePickerAsset,
  includeBase64: boolean,
): PickedImage | null {
  if (includeBase64 && !asset.base64) return null;
  return {
    uri: asset.uri,
    base64: asset.base64 ?? '',
    mimeType: inferMime(asset.uri, asset.mimeType),
    width: asset.width ?? 0,
    height: asset.height ?? 0,
    fileSize: asset.fileSize ?? null,
  };
}

async function normalizeToJpeg(
  asset: ImagePicker.ImagePickerAsset,
  includeBase64: boolean,
): Promise<PickedImage | null> {
  try {
    const normalized = await ImageManipulator.manipulateAsync(asset.uri, [], {
      format: ImageManipulator.SaveFormat.JPEG,
      compress: 0.9,
      base64: includeBase64,
    });
    if (includeBase64 && !normalized.base64) {
      throw new Error('NORMALIZED_IMAGE_BASE64_MISSING');
    }
    let fileSize: number | null = null;
    try {
      const info = await getInfoAsync(normalized.uri);
      fileSize = info.exists ? info.size : null;
    } catch (error) {
      logger.warn(
        'pickDiseaseImage',
        'normalized image size lookup failed:',
        error,
      );
    }
    return {
      uri: normalized.uri,
      base64: normalized.base64 ?? '',
      mimeType: 'image/jpeg',
      width: normalized.width,
      height: normalized.height,
      fileSize,
    };
  } catch (error) {
    logger.warn(
      'pickDiseaseImage',
      'JPEG normalization failed; using original image:',
      error,
    );
    return toPicked(asset, includeBase64);
  }
}

export async function captureFromCamera(
  options: { base64?: boolean } = {},
): Promise<PickedImage | null> {
  try {
    const includeBase64 = options.base64 ?? true;
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      console.warn('[pickDiseaseImage] Camera permission denied');
      Alert.alert(
        i18next.t('disease.cameraPermissionTitle'),
        i18next.t('disease.cameraPermissionMessage'),
      );
      return null;
    }
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      quality: 0.6,
      base64: includeBase64,
    });
    if (result.canceled) {
      console.warn('[pickDiseaseImage] Camera capture cancelled');
      return null;
    }
    if (!result.assets.length) {
      console.warn('[pickDiseaseImage] Camera returned no image');
      return null;
    }
    return normalizeToJpeg(result.assets[0], includeBase64);
  } catch (e) {
    logger.warn('captureFromCamera', e);
    Alert.alert(i18next.t('disease.photoOpenFailed'));
    return null;
  }
}

export async function pickFromGallery(
  options: { base64?: boolean } = {},
): Promise<PickedImage | null> {
  try {
    const includeBase64 = options.base64 ?? true;
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      console.warn('[pickDiseaseImage] Photo library permission denied');
      Alert.alert(
        i18next.t('disease.galleryPermissionTitle'),
        i18next.t('disease.galleryPermissionMessage'),
      );
      return null;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.6,
      base64: includeBase64,
    });
    if (result.canceled) {
      console.warn('[pickDiseaseImage] Photo selection cancelled');
      return null;
    }
    if (!result.assets.length) {
      console.warn('[pickDiseaseImage] Photo library returned no image');
      return null;
    }
    return normalizeToJpeg(result.assets[0], includeBase64);
  } catch (e) {
    logger.warn('pickFromGallery', e);
    Alert.alert(i18next.t('disease.photoOpenFailed'));
    return null;
  }
}

/** Native asynchronous file read used only immediately before backend upload. */
export function readDiseaseImageBase64(uri: string): Promise<string> {
  return readAsStringAsync(uri, { encoding: EncodingType.Base64 });
}
