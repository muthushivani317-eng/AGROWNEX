import { useTranslation } from 'react-i18next';

import { AgBadge } from '@/components/ui';

import { SEVERITY_TONE } from '../constants';
import type { Severity } from '../types';

const LABEL_KEY: Record<Severity, string> = {
  none: 'disease.severityNone',
  low: 'disease.severityLow',
  moderate: 'disease.severityModerate',
  high: 'disease.severityHigh',
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const { t } = useTranslation();
  return <AgBadge label={t(LABEL_KEY[severity])} tone={SEVERITY_TONE[severity]} />;
}
