import { useTranslation } from 'react-i18next';

import { AgBadge } from '@/components/ui';

import type { FarmStatus } from '../types';

const TONE: Record<FarmStatus, 'neutral' | 'success' | 'warning' | 'info'> = {
  draft: 'neutral',
  active: 'success',
  harvested: 'warning',
  archived: 'info',
};

const LABEL_KEY: Record<FarmStatus, string> = {
  draft: 'farm.statusDraft',
  active: 'farm.statusActive',
  harvested: 'farm.statusHarvested',
  archived: 'farm.statusArchived',
};

export function FarmStatusBadge({ status }: { status: FarmStatus }) {
  const { t } = useTranslation();
  return <AgBadge label={t(LABEL_KEY[status])} tone={TONE[status]} />;
}
