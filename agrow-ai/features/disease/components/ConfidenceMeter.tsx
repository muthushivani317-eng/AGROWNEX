import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

/** Confidence bar (0-100) coloured by band. */
export function ConfidenceMeter({ value }: { value: number | null }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const hasConfidence = Number.isFinite(value);
  const pct = hasConfidence ? Math.max(0, Math.min(100, value as number)) : 0;
  const tone =
    pct >= 75 ? colors.success : pct >= 50 ? colors.warning : colors.danger;

  return (
    <View>
      <View style={{ marginBottom: 4, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <AgText variant="caption" color="muted">
          {t('disease.confidence')}
        </AgText>
        <AgText variant="caption" weight="semibold">
          {hasConfidence ? `${Math.round(pct)}%` : t('disease.confidenceUnavailable')}
        </AgText>
      </View>
      <View style={{ height: 8, width: '100%', overflow: 'hidden', borderRadius: 8, backgroundColor: colors.border }}>
        <View style={{ height: '100%', borderRadius: 8, backgroundColor: tone, width: `${pct}%` }} />
      </View>
    </View>
  );
}
