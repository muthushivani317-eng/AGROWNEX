import { buildProfile, env, isS3Configured } from '@/config/env';
import { logger } from '@/lib/logger';

/**
 * Image upload service (docs/FRONTEND_ARCHITECTURE.md → IMAGE PIPELINE,
 * docs/BACKEND_ARCHITECTURE.md → Storage). Uploads a locally-picked image and
 * returns the URL to persist on the profile.
 *
 * Two real implementations, chosen by config (mirrors the mock↔firebase auth
 * provider): S3 when an upload endpoint is configured, otherwise a local mock
 * that keeps the on-device URI so the avatar still renders in development.
 */

type MimeType = 'image/jpeg' | 'image/png' | 'image/webp';

function guessMime(fileName: string): MimeType {
  const ext = fileName.toLowerCase().split('.').pop();
  if (ext === 'png') return 'image/png';
  if (ext === 'webp') return 'image/webp';
  return 'image/jpeg';
}

async function mockUpload(localUri: string): Promise<string> {
  // No cloud in local dev — the device URI is the stored reference and renders
  // directly. Replaced by the S3 path once EXPO_PUBLIC_S3_UPLOAD_ENDPOINT is set.
  logger.info('upload', 'mock avatar upload', localUri);
  return localUri;
}

async function s3Upload(localUri: string, folder: string): Promise<string> {
  const fileName = localUri.split('/').pop() ?? `photo-${Date.now()}.jpg`;
  const form = new FormData();
  form.append('folder', folder);
  form.append('file', {
    uri: localUri,
    name: fileName,
    type: guessMime(fileName),
  } as unknown as Blob);

  const res = await fetch(env.s3.uploadEndpoint, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`upload_failed_${res.status}`);
  const data = (await res.json()) as { url: string };
  return data.url;
}

export const uploadService = {
  /** Upload an image and return its persisted URL. `folder` groups by domain. */
  async uploadImage(localUri: string, folder = 'profiles'): Promise<string> {
    if (isS3Configured) return s3Upload(localUri, folder);
    if (
      buildProfile === 'production' ||
      buildProfile === 'internal_testing' ||
      buildProfile === 'kvk_field_test'
    ) {
      throw new Error('upload_provider_not_configured');
    }
    return mockUpload(localUri);
  },
};
