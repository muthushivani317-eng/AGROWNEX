import { CloudRain, type LucideIcon, Sprout, UserRound } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgCard, AgText } from '@/components/ui';
import { CATEGORY_LABEL_KEY } from '@/features/weather/constants';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { ActivityItem, ActivityKind } from '../types';
import { relativeTimeKey } from '../utils/time';

const KIND_ICON: Record<ActivityKind, LucideIcon> = {
  farm: Sprout,
  profile: UserRound,
  weather: CloudRain,
};

export function RecentActivity({ activity }: { activity: ActivityItem[] }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  return (
    <View>
      <AgText variant="label" weight="semibold" color="muted" className="mb-2">
        {t('home.recentActivity')}
      </AgText>
      <AgCard className="gap-1 py-2">
        {activity.length ? (
          activity.map((item) => {
            const Icon = KIND_ICON[item.kind];
            const rt = relativeTimeKey(item.timestamp);
            const title =
              item.kind === 'weather'
                ? t(item.titleKey, {
                    category: item.category
                      ? t(CATEGORY_LABEL_KEY[
                          item.category as keyof typeof CATEGORY_LABEL_KEY
                        ])
                      : '',
                  })
                : t(item.titleKey, item.params);
            return (
              <View key={item.id} className="flex-row items-center gap-3 py-2.5">
                <View className="h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                  <Icon size={16} color={colors.primary} />
                </View>
                <AgText variant="bodySmall" className="flex-1" numberOfLines={1}>
                  {title}
                </AgText>
                <AgText variant="caption" color="disabled">
                  {t(rt.key, rt.params)}
                </AgText>
              </View>
            );
          })
        ) : (
          <AgText variant="body" color="muted" center className="py-3">
            {t('home.noActivity')}
          </AgText>
        )}
      </AgCard>
    </View>
  );
}
