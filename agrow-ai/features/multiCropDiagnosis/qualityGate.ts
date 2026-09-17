export type QualityIssue =
  | 'decode_failed'
  | 'dimensions_too_small'
  | 'extreme_blur'
  | 'extreme_exposure'
  | 'nearly_blank';

export interface DecodedImageSignals {
  decoded: boolean;
  width: number;
  height: number;
  /** Optional value calculated by a native/backend decoder, never by a crop model. */
  luminanceMean?: number;
  luminanceVariance?: number;
  uniformPixelRatio?: number;
}

/** Non-diagnostic checks only. They do not recognize or verify crop identity. */
export function evaluateImageQuality(signals: DecodedImageSignals): QualityIssue[] {
  const issues: QualityIssue[] = [];
  if (!signals.decoded) return ['decode_failed'];
  if (Math.min(signals.width, signals.height) < 224) issues.push('dimensions_too_small');
  if (signals.luminanceVariance != null && signals.luminanceVariance < 8) {
    issues.push('extreme_blur');
  }
  if (signals.luminanceMean != null && (signals.luminanceMean < 5 || signals.luminanceMean > 250)) {
    issues.push('extreme_exposure');
  }
  if (signals.uniformPixelRatio != null && signals.uniformPixelRatio >= 0.98) {
    issues.push('nearly_blank');
  }
  return Array.from(new Set(issues));
}
