import { BarChart3, Camera, MessageSquare } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { BananaPredictionResponse } from '../types';
import { qualitativeConfidence, safeMessageKey } from '../responseMapping';

export function BananaPredictionResult({
  response,
  onRetake,
  onFeedback,
}: {
  response: BananaPredictionResponse;
  onRetake: () => void;
  onFeedback: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const percentage = Number.isFinite(response.result.confidence)
    ? Math.round(response.result.confidence * 100)
    : null;
  const diseaseLabel = response.result.display_name_key
    ? t(response.result.display_name_key)
    : null;

  return (
    <View
      testID="banana-prediction-result"
      style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}
    >
      <View style={styles.headingRow}>
        <BarChart3 size={23} color={colors.primaryLight} />
        <AgText variant="bodyLarge" weight="semibold">{t('banana.ui.resultTitle')}</AgText>
      </View>

      <View style={styles.resultCopy}>
        <AgText variant="bodySmall" color="muted">
          {t('banana.ui.crop')}: <AgText variant="bodySmall" weight="semibold" color="primary">{t('banana.ui.banana')}</AgText>
        </AgText>
        <AgText variant="body">{t(safeMessageKey(response))}</AgText>
        {diseaseLabel ? (
          <View style={styles.dataRow}>
            <AgText variant="bodySmall" color="muted">{t('disease.diseaseLabel')}</AgText>
            <AgText variant="body" weight="semibold" color="primary" style={styles.dataValue}>{diseaseLabel}</AgText>
          </View>
        ) : null}
        <View style={styles.dataRow}>
          <AgText variant="bodySmall" color="muted">{t('banana.ui.confidence')}</AgText>
          <View style={styles.confidenceCopy}>
            <AgText variant="bodySmall" weight="semibold" color="primary">
              {percentage === null
                ? t('disease.confidenceUnavailable')
                : t(`banana.ui.confidence${qualitativeConfidence(response.result.confidence)}`)}
            </AgText>
            {percentage !== null ? (
              <AgText variant="bodySmall" weight="semibold">
                {t('disease.diagnosisConfidence', { confidence: percentage })}
              </AgText>
            ) : null}
          </View>
        </View>
      </View>

      <Pressable
        onPress={onRetake}
        accessibilityRole="button"
        accessibilityLabel={t('banana.ui.takeAnother')}
        style={({ pressed }) => [styles.primaryAction, { backgroundColor: colors.primary, opacity: pressed ? 0.76 : 1 }]}
      >
        <Camera size={20} color={colors.onPrimary} />
        <AgText variant="body" weight="semibold" color="onPrimary">{t('banana.ui.takeAnother')}</AgText>
      </Pressable>
      <Pressable
        onPress={onFeedback}
        accessibilityRole="button"
        accessibilityLabel={t('banana.ui.submitFeedback')}
        style={({ pressed }) => [styles.feedbackAction, { borderColor: colors.border, opacity: pressed ? 0.7 : 1 }]}
      >
        <MessageSquare size={18} color={colors.textMuted} />
        <AgText variant="bodySmall" color="muted" weight="medium">{t('banana.ui.submitFeedback')}</AgText>
      </Pressable>

      {__DEV__ ? (
        <View testID="banana-dev-diagnostics" style={[styles.diagnostics, { borderTopColor: colors.border }]}>
          <AgText variant="caption" color="muted">
            {t('banana.ui.diagnosticsRuntime', {
              modelVersion: response.model_version,
              runtimeBackend: response.runtime_backend,
              processingTimeMs: response.processing_time_ms,
            })}
          </AgText>
          <AgText variant="caption" color="muted">
            {t('banana.ui.diagnosticsGates', {
              decisionCode: response.decision_code,
              healthyConfidence: response.healthy_gate.confidence,
              healthyMargin: response.healthy_gate.margin,
              diseaseConfidence: response.disease_classifier.confidence,
              diseaseMargin: response.disease_classifier.margin,
            })}
          </AgText>
          <AgText variant="caption" color="muted">
            {t('banana.ui.diagnosticsRequest', { requestId: response.request_id })}
          </AgText>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 22, padding: 16, gap: 14, marginTop: 16 },
  headingRow: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  resultCopy: { gap: 9 },
  dataRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 },
  dataValue: { flex: 1, textAlign: 'right' },
  confidenceCopy: { flex: 1, alignItems: 'flex-end', gap: 2 },
  primaryAction: { minHeight: 52, borderRadius: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 9, paddingHorizontal: 16 },
  feedbackAction: { minHeight: 44, borderTopWidth: StyleSheet.hairlineWidth, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingTop: 10 },
  diagnostics: { borderTopWidth: StyleSheet.hairlineWidth, paddingTop: 10, gap: 2 },
});
