import { AgButton, AgCard, AgText } from '@/components/ui';
import { useTranslation } from 'react-i18next';

export function AcceptedDiagnosisCard(props: { title: string; explanation: string; confidence: number; onFeedback: () => void }) {
  const { t } = useTranslation();
  const confidence = Number.isFinite(props.confidence)
    ? t('disease.diagnosisConfidence', { confidence: Math.round(props.confidence * 100) })
    : t('disease.confidenceUnavailable');
  return <AgCard className="mt-4 gap-2"><AgText weight="bold">{props.title}</AgText><AgText weight="semibold">{confidence}</AgText><AgText color="muted">{props.explanation}</AgText><AgButton title={t('disease.provideFeedback')} onPress={props.onFeedback} /></AgCard>;
}

export function UncertainDiagnosisCard({
  onRetake,
  onCheckNutrients,
}: {
  onRetake: () => void;
  onCheckNutrients?: () => void;
}) {
  const { t } = useTranslation();
  return <AgCard className="mt-4 gap-2">
    <AgText weight="bold">{t('disease.uncertainTitle')}</AgText>
    <AgText color="muted">
      {t('disease.uncertainMessage')}
    </AgText>
    <AgButton title={t('disease.retakePhoto')} onPress={onRetake} />
    {onCheckNutrients ? <AgButton title={t('disease.checkNutrientSymptoms')} variant="secondary" onPress={onCheckNutrients} /> : null}
  </AgCard>;
}

export function DiagnosisErrorCard(props: { message: string; onRetry: () => void }) {
  const { t } = useTranslation();
  return <AgCard className="mt-4 gap-2"><AgText color="danger">{props.message}</AgText><AgButton title={t('common.retry')} onPress={props.onRetry} /></AgCard>;
}

export function DiagnosisFeedbackCard({ onSubmit }: { onSubmit: () => void }) {
  const { t } = useTranslation();
  return <AgCard className="mt-4"><AgButton title={t('disease.submitFeedback')} onPress={onSubmit} /></AgCard>;
}
