import { useTranslation } from 'react-i18next';
import { AgButton, AgCard, AgText } from '@/components/ui';

export function BananaUncertainResult({ onRetake }: { onRetake: () => void }) {
  const { t } = useTranslation();
  return (
    <AgCard className="mt-4 gap-3" testID="banana-uncertain-result">
      <AgText variant="headingS" weight="bold">{t('banana.ui.unableTitle')}</AgText>
      <AgText variant="body">{t('banana.result.unable_to_confirm')}</AgText>
      <AgText variant="bodySmall" color="muted">{t('banana.ui.retakeInstructions')}</AgText>
      <AgButton title={t('banana.ui.retake')} onPress={onRetake} />
    </AgCard>
  );
}
