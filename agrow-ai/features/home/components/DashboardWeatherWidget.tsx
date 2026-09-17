import { ChevronRight, Droplet, MapPinOff } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import {
  AgBadge,
  AgButton,
  AgCard,
  AgPressable,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import {
  CONDITION_LABEL_KEY,
  INSIGHT_MESSAGE_KEY,
} from '@/features/weather/constants';
import type { WeatherBundle, WeatherInsight } from '@/features/weather';
import { formatTempUnit } from '@/features/weather/utils/format';
import { CATEGORY_ICON, conditionIcon } from '@/features/weather/utils/weatherIcons';
import { useAppTheme } from '@/hooks/useAppTheme';

const SEVERITY_RANK: Record<WeatherInsight['severity'], number> = {
  critical: 3,
  warning: 2,
  advice: 1,
  info: 0,
};

function topInsight(insights: WeatherInsight[]): WeatherInsight | null {
  return (
    [...insights].sort(
      (a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity],
    )[0] ?? null
  );
}

export function DashboardWeatherWidget({
  weather,
  loading,
  hasFarm,
  hasCoords,
  error,
  onPress,
  onAddLocation,
  onRetry,
}: {
  weather: WeatherBundle | null;
  loading: boolean;
  hasFarm: boolean;
  hasCoords: boolean;
  error: boolean;
  onPress: () => void;
  onAddLocation: () => void;
  onRetry: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  if (!hasFarm) return null;

  if (!hasCoords) {
    return (
      <AgCard className="flex-row items-center gap-3">
        <View className="h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <MapPinOff size={20} color={colors.primary} />
        </View>
        <View className="flex-1">
          <AgText variant="body" weight="semibold">
            {t('weather.noLocationTitle')}
          </AgText>
          <AgText variant="caption" color="muted">
            {t('weather.noLocationMessage')}
          </AgText>
        </View>
        <AgButton
          title={t('weather.addLocation')}
          size="sm"
          variant="secondary"
          fullWidth={false}
          onPress={onAddLocation}
        />
      </AgCard>
    );
  }

  if (loading && !weather) {
    return <AgSkeleton className="h-32 w-full rounded-card" />;
  }

  if ((error && !weather) || !weather) {
    return (
      <AgCard className="items-center gap-2 py-5">
        <AgText variant="body" color="muted">
          {t('weather.errorMessage')}
        </AgText>
        <AgButton
          title={t('common.retry')}
          size="sm"
          variant="secondary"
          fullWidth={false}
          onPress={onRetry}
        />
      </AgCard>
    );
  }

  const { current, daily, insights } = weather;
  const Icon = conditionIcon(current.condition, current.isDay);
  const rainProb =
    daily[0]?.precipitationProbabilityMaxPct ??
    weather.hourly[0]?.precipitationProbabilityPct ??
    0;
  const alertCount = insights.filter(
    (i) => i.severity === 'warning' || i.severity === 'critical',
  ).length;
  const advice = topInsight(insights);
  const AdviceIcon = advice ? CATEGORY_ICON[advice.category] : null;
  const adviceKey = advice ? INSIGHT_MESSAGE_KEY[advice.code] : undefined;
  const adviceText = advice
    ? adviceKey
      ? t(adviceKey, advice.params)
      : advice.message
    : null;

  return (
    <AgPressable onPress={onPress} accessibilityRole="button" accessibilityLabel={t('weather.title')}>
      <AgCard variant="elevated">
        <View className="flex-row items-center gap-3">
          <Icon size={48} color={colors.primary} strokeWidth={1.5} />
          <View className="flex-1">
            <AgText variant="headingL" weight="bold">
              {formatTempUnit(current.temperatureC)}
            </AgText>
            <AgText variant="bodySmall" color="muted">
              {t(CONDITION_LABEL_KEY[current.condition])}
            </AgText>
          </View>
          <View className="items-end gap-1">
            {alertCount > 0 ? (
              <AgBadge label={`${alertCount}`} tone="warning" />
            ) : null}
            <View className="flex-row items-center gap-1">
              <Droplet size={13} color={colors.info} />
              <AgText variant="caption" color="muted">
                {rainProb}%
              </AgText>
            </View>
            <ChevronRight size={18} color={colors.textMuted} />
          </View>
        </View>

        {advice && adviceText ? (
          <>
            <View className="my-3 h-px bg-border" />
            <View className="flex-row items-center gap-2">
              {AdviceIcon ? <AdviceIcon size={16} color={colors.primary} /> : null}
              <AgText variant="bodySmall" className="flex-1" numberOfLines={2}>
                {adviceText}
              </AgText>
            </View>
          </>
        ) : null}
      </AgCard>
    </AgPressable>
  );
}
