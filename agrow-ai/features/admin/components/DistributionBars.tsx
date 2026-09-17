import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgCard, AgText } from '@/components/ui';

import type { DistributionItem } from '../types';

/**
 * A labelled horizontal bar chart for a category distribution. Bars are scaled to the
 * largest value; an empty distribution shows an honest “no data” line rather than a
 * fabricated chart.
 */
export function DistributionBars({
  title,
  items,
}: {
  title: string;
  items: DistributionItem[];
}) {
  const { t } = useTranslation();
  const max = items.reduce((m, i) => Math.max(m, i.count), 0);
  return (
    <AgCard className="gap-3">
      <AgText variant="label" weight="semibold">
        {title}
      </AgText>
      {items.length === 0 ? (
        <AgText variant="caption" color="muted">
          {t('admin.noData')}
        </AgText>
      ) : (
        items.map((item) => (
          <View key={item.label} className="gap-1">
            <View className="flex-row items-center justify-between">
              <AgText variant="caption" className="flex-1" numberOfLines={1}>
                {item.label}
              </AgText>
              <AgText variant="caption" weight="semibold" color="muted">
                {item.count}
              </AgText>
            </View>
            <View className="h-2 overflow-hidden rounded-full bg-border/60">
              <View
                className="h-2 rounded-full bg-primary"
                style={{ width: `${max ? Math.round((item.count / max) * 100) : 0}%` }}
              />
            </View>
          </View>
        ))
      )}
    </AgCard>
  );
}
