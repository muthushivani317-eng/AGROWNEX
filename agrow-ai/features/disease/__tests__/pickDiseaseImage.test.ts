const mockLaunchImageLibraryAsync = jest.fn();
const mockLaunchCameraAsync = jest.fn();
const mockManipulateAsync = jest.fn();
const mockGetInfoAsync = jest.fn();
const mockReadAsStringAsync = jest.fn();
import { Alert } from 'react-native';

jest.mock('expo-image-picker', () => ({
  requestCameraPermissionsAsync: jest.fn().mockResolvedValue({ granted: true }),
  requestMediaLibraryPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ granted: true }),
  launchCameraAsync: (...args: unknown[]) => mockLaunchCameraAsync(...args),
  launchImageLibraryAsync: (...args: unknown[]) =>
    mockLaunchImageLibraryAsync(...args),
}));
jest.mock('expo-image-manipulator', () => ({
  SaveFormat: { JPEG: 'jpeg' },
  manipulateAsync: (...args: unknown[]) => mockManipulateAsync(...args),
}));
jest.mock('expo-file-system/legacy', () => ({
  EncodingType: { Base64: 'base64' },
  getInfoAsync: (...args: unknown[]) => mockGetInfoAsync(...args),
  readAsStringAsync: (...args: unknown[]) => mockReadAsStringAsync(...args),
}));

import {
  captureFromCamera,
  pickFromGallery,
  readDiseaseImageBase64,
} from '../utils/pickDiseaseImage';

beforeEach(() => {
  jest.clearAllMocks();
  mockManipulateAsync.mockResolvedValue({
    uri: 'file:///normalized.jpg',
    width: 1000,
    height: 1000,
  });
  mockGetInfoAsync.mockResolvedValue({
    exists: true,
    uri: 'file:///normalized.jpg',
    size: 45_000,
    isDirectory: false,
    modificationTime: 0,
  });
});

test('picker does not synchronously request base64 image processing', async () => {
  mockLaunchImageLibraryAsync.mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: 'file:///leaf.jpg',
        mimeType: 'image/jpeg',
        width: 1000,
        height: 1000,
        fileSize: 50_000,
      },
    ],
  });
  await expect(pickFromGallery({ base64: false })).resolves.toMatchObject({
    uri: 'file:///normalized.jpg',
    mimeType: 'image/jpeg',
    fileSize: 45_000,
  });
  expect(mockLaunchImageLibraryAsync).toHaveBeenCalledWith(
    expect.objectContaining({ base64: false }),
  );
  expect(mockReadAsStringAsync).not.toHaveBeenCalled();
});

test('camera and gallery both normalize selected images to JPEG', async () => {
  const asset = {
    uri: 'file:///leaf.heic',
    mimeType: 'image/heic',
    width: 1200,
    height: 900,
    fileSize: 80_000,
  };
  mockLaunchCameraAsync.mockResolvedValue({ canceled: false, assets: [asset] });
  mockLaunchImageLibraryAsync.mockResolvedValue({
    canceled: false,
    assets: [asset],
  });

  await expect(captureFromCamera({ base64: false })).resolves.toMatchObject({
    uri: 'file:///normalized.jpg',
    mimeType: 'image/jpeg',
  });
  await expect(pickFromGallery({ base64: false })).resolves.toMatchObject({
    uri: 'file:///normalized.jpg',
    mimeType: 'image/jpeg',
  });
  expect(mockManipulateAsync).toHaveBeenCalledTimes(2);
  expect(mockManipulateAsync).toHaveBeenCalledWith('file:///leaf.heic', [], {
    format: 'jpeg',
    compress: 0.9,
    base64: false,
  });
});

test('normalization failure falls back to the original picker asset', async () => {
  const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
  mockManipulateAsync.mockRejectedValueOnce(new Error('conversion failed'));
  mockLaunchImageLibraryAsync.mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: 'file:///leaf.heic',
        mimeType: 'image/heic',
        width: 900,
        height: 700,
        fileSize: 80_000,
      },
    ],
  });

  await expect(pickFromGallery({ base64: false })).resolves.toMatchObject({
    uri: 'file:///leaf.heic',
    mimeType: 'image/heic',
  });
  expect(warn).toHaveBeenCalledWith(
    '[pickDiseaseImage]',
    'JPEG normalization failed; using original image:',
    expect.any(Error),
  );
  warn.mockRestore();
});

test('image bytes are read through the asynchronous native file API', async () => {
  mockReadAsStringAsync.mockResolvedValue('encoded');
  await expect(readDiseaseImageBase64('file:///leaf.jpg')).resolves.toBe(
    'encoded',
  );
  expect(mockReadAsStringAsync).toHaveBeenCalledWith('file:///leaf.jpg', {
    encoding: 'base64',
  });
});

test.each(['camera', 'gallery'])('%s native failure alerts instead of silently cancelling', async (source) => {
  const alert = jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  const launch = source === 'camera' ? mockLaunchCameraAsync : mockLaunchImageLibraryAsync;
  launch.mockRejectedValueOnce(new Error('native picker failed'));
  const result = await (source === 'camera' ? captureFromCamera() : pickFromGallery());
  expect(result).toBeNull();
  expect(alert).toHaveBeenCalledTimes(1);
  alert.mockRestore();
});

test('user cancellation does not show an error alert', async () => {
  const alert = jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  mockLaunchImageLibraryAsync.mockResolvedValueOnce({ canceled: true, assets: [] });
  expect(await pickFromGallery()).toBeNull();
  expect(alert).not.toHaveBeenCalled();
  alert.mockRestore();
});
