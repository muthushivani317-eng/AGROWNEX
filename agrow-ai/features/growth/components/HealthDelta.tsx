import { Minus, TrendingDown, TrendingUp } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

/** Small health-change indicator vs the previous week (↑ improving / ↓ concern). */
export function HealthDelta({ delta }: { delta: number | null }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  if (delta == null || delta === 0) {
    return (
      <View className="flex-row items-center gap-1">
        <Minus size={14} color={colors.textMuted} />
        <AgText variant="caption" style={styles.muted}>
          {t('growth.deltaSame')}
        </AgText>
      </View>
    );
  }
  const improving = delta > 0;
  const color = improving ? colors.success : colors.danger;
  const Icon = improving ? TrendingUp : TrendingDown;
  return (
    <View className="flex-row items-center gap-1">
      <Icon size={14} color={color} />
      <AgText variant="caption" weight="semibold" style={{ color }}>
        {improving ? '+' : ''}
        {delta}
      </AgText>
    </View>
  );
}

const styles = StyleSheet.create({
  muted: { color: '#536158' },
});
