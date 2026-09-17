import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgText } from '@/components/ui';

import { CONFIDENCE_MODERATE, CONFIDENCE_STRONG } from '../constants';

/**
 * Confidence bar (0-100), coloured by band. A farm-health assessment is never presented
 * as certain — low coverage (missing modules) is shown as low confidence, honestly.
 */
export function ConfidenceMeter({ value }: { value: number | null }) {
  const { t } = useTranslation();
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const tone =
    pct >= CONFIDENCE_STRONG ? 'bg-success' : pct >= CONFIDENCE_MODERATE ? 'bg-warning' : 'bg-danger';

  return (
    <View accessibilityLabel={`${t('intelligence.confidence')} ${Math.round(pct)}%`}>
      <View className="mb-1 flex-row items-center justify-between">
        <AgText variant="caption" color="muted">
          {t('intelligence.confidence')}
        </AgText>
        <AgText variant="caption" weight="semibold">
          {value == null ? '—' : `${Math.round(pct)}%`}
        </AgText>
      </View>
      <View className="h-2 w-full overflow-hidden rounded-full bg-border">
        <View className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </View>
      {pct < CONFIDENCE_MODERATE ? (
        <AgText variant="caption" color="muted" className="mt-1">
          {t('intelligence.lowConfidenceHint')}
        </AgText>
      ) : null}
    </View>
  );
}
