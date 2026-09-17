import { useTranslation } from 'react-i18next';

import { AgBadge } from '@/components/ui';

import { STATUS_LABEL_KEY, STATUS_TONE } from '../constants';
import type { ProduceStatus } from '../types';

/** Localized badge for a produce offer's procurement lifecycle status. */
export function ProduceStatusBadge({ status }: { status: ProduceStatus }) {
  const { t } = useTranslation();
  return <AgBadge label={t(STATUS_LABEL_KEY[status])} tone={STATUS_TONE[status]} />;
}
