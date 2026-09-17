import { useTranslation } from 'react-i18next';

import { AgBadge } from '@/components/ui';

import { HARVEST_WINDOW_LABEL_KEY, HARVEST_WINDOW_TONE } from '../constants';
import type { HarvestWindow } from '../types';

/** Localized badge for how soon a harvest is due (from the procurement engine). */
export function HarvestWindowBadge({ window }: { window: HarvestWindow }) {
  const { t } = useTranslation();
  return (
    <AgBadge
      label={t(HARVEST_WINDOW_LABEL_KEY[window])}
      tone={HARVEST_WINDOW_TONE[window]}
    />
  );
}
