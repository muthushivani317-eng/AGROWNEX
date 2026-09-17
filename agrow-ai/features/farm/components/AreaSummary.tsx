import { useTranslation } from 'react-i18next';

import { AgText, type AgTextProps } from '@/components/ui';

import { hectaresToAcres } from '../utils/geo';

/** Renders an area in hectares + acres, or a "no area" hint. */
export function AreaSummary({
  hectares,
  variant = 'body',
}: {
  hectares: number | null;
  variant?: AgTextProps['variant'];
}) {
  const { t } = useTranslation();
  if (hectares == null) {
    return (
      <AgText variant={variant} color="muted">
        {t('farm.noArea')}
      </AgText>
    );
  }
  return (
    <AgText variant={variant} weight="semibold">
      {hectares.toFixed(2)} {t('farm.hectaresShort')} · {hectaresToAcres(hectares).toFixed(2)}{' '}
      {t('farm.acresShort')}
    </AgText>
  );
}
