import {
  ALLOWED_MIME_TYPES,
  MAX_IMAGE_BYTES,
  MIN_DIMENSION_PX,
  MIN_IMAGE_BYTES,
} from '../constants';
import type { PickedImage } from '../types';

/**
 * Client-side quality pre-check (docs: STEP 1). Deterministic and pure — catches
 * the issues we can measure on-device (resolution, size, format) BEFORE upload,
 * so poor images are never sent. The backend re-validates (incl. blur/brightness
 * via Pillow) as a guard. Returned codes localize via `QUALITY_ISSUE_KEY`.
 */
export interface ClientQualityResult {
  ok: boolean;
  issues: string[];
}

export function checkImageQuality(
  image: Pick<PickedImage, 'width' | 'height' | 'fileSize' | 'mimeType'>,
): ClientQualityResult {
  const issues: string[] = [];

  if (image.mimeType && !ALLOWED_MIME_TYPES.includes(image.mimeType)) {
    issues.push('unsupported_type');
  }
  if (image.fileSize != null) {
    if (image.fileSize < MIN_IMAGE_BYTES) issues.push('too_small');
    else if (image.fileSize > MAX_IMAGE_BYTES) issues.push('too_large');
  }
  if (image.width > 0 && image.height > 0) {
    if (Math.min(image.width, image.height) < MIN_DIMENSION_PX) {
      issues.push('too_small');
    }
  }

  const unique = Array.from(new Set(issues));
  return { ok: unique.length === 0, issues: unique };
}
