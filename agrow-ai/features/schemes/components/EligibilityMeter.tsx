import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgText } from '@/components/ui';

import { STATUS_LABEL_KEY, STATUS_TONE } from '../constants';
import type { Eligibility } from '../types';

/**
 * Eligibility meter (docs: Scheme Detail → Eligibility Meter). A transparent
 * 0-100 match score coloured by the engine's verdict, with the status label.
 */
export function EligibilityMeter({
  eligibility,
  showScore = true,
}: {
  eligibility: Eligibility | null;
  showScore?: boolean;
}) {
  const { t } = useTranslation();
  if (!eligibility) return null;

  const pct = Math.max(0, Math.min(100, eligibility.score));
  const tone = STATUS_TONE[eligibility.status];
  const barColor =
    tone === 'success'
      ? 'bg-success'
      : tone === 'warning'
        ? 'bg-warning'
        : 'bg-danger';

  return (
    <View>
      <View className="mb-1.5 flex-row items-center justify-between">
        <AgBadge label={t(STATUS_LABEL_KEY[eligibility.status])} tone={tone} />
        {showScore ? (
          <AgText variant="caption" color="muted" weight="semibold">
            {t('schemes.matchScore', { score: Math.round(pct) })}
          </AgText>
        ) : null}
      </View>
      <View
        className="h-2 w-full overflow-hidden rounded-full bg-border"
        accessibilityRole="progressbar"
        accessibilityValue={{ now: Math.round(pct), min: 0, max: 100 }}
      >
        <View className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </View>
    </View>
  );
}
