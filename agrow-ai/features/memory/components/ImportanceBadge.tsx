import { useTranslation } from 'react-i18next';

import { AgBadge } from '@/components/ui';

import { IMPORTANCE_LABEL_KEY, IMPORTANCE_TONE } from '../constants';
import type { MemoryImportance } from '../types';

/** A memory's importance as a coloured badge (low → critical). */
export function ImportanceBadge({ importance }: { importance: MemoryImportance }) {
  const { t } = useTranslation();
  return (
    <AgBadge label={t(IMPORTANCE_LABEL_KEY[importance])} tone={IMPORTANCE_TONE[importance]} />
  );
}
