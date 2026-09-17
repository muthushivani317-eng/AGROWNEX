import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgCard, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { OVERVIEW_LABEL_KEY } from '../constants';
import type { OverviewCard } from '../types';
import { formatCount, metricIcon } from './adminMeta';

/** One dashboard overview tile. A null value is surfaced as “—”, never fabricated. */
export function MetricCard({ card }: { card: OverviewCard }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon = metricIcon(card.key);
  return (
    <AgCard variant="compact" className="min-w-[46%] flex-1 gap-2">
      <View className="h-9 w-9 items-center justify-center rounded-md bg-primary/10">
        <Icon size={18} color={colors.primary} />
      </View>
      <AgText variant="headingS" weight="bold">
        {formatCount(card.value)}
      </AgText>
      <AgText variant="caption" color="muted" numberOfLines={2}>
        {t(OVERVIEW_LABEL_KEY[card.key] ?? card.key)}
      </AgText>
    </AgCard>
  );
}
