import { formatDiagnosisName } from '@/features/disease/utils/diagnosisName';

/** Format labels for interpolation only; leave the stored notification intact. */
export function notificationDisplayPayload(payload: Record<string, unknown>): Record<string, unknown> {
  return {
    ...payload,
    ...(typeof payload.disease === 'string'
      ? { disease: formatDiagnosisName(payload.disease) ?? payload.disease }
      : {}),
  };
}
