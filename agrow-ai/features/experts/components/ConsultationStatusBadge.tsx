import { useTranslation } from 'react-i18next';

import { AgBadge } from '@/components/ui';

import { STATUS_LABEL_KEY, STATUS_TONE } from '../constants';
import type { ConsultationStatus } from '../types';

export function ConsultationStatusBadge({ status }: { status: ConsultationStatus }) {
  const { t } = useTranslation();
  return <AgBadge label={t(STATUS_LABEL_KEY[status])} tone={STATUS_TONE[status]} />;
}
