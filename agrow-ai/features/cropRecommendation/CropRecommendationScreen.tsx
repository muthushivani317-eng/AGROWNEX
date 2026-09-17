import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgBadge, AgButton, AgCard, AgInput, AgScreen, AgText } from '@/components/ui';
import { internalTestFlags } from '@/config/internalTestFlags';

import {
  recommendCrop,
  type CropRecommendationInput,
  type CropRecommendationResult,
} from './cropRecommendationApi';

type Field = keyof CropRecommendationInput;
const FIELDS: Field[] = [
  'nitrogen', 'phosphorus', 'potassium', 'temperature_c',
  'humidity_percent', 'ph', 'rainfall_mm',
];

export function CropRecommendationScreen() {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<Field, string>>({
    nitrogen: '', phosphorus: '', potassium: '', temperature_c: '',
    humidity_percent: '', ph: '', rainfall_mm: '',
  });
  const [result, setResult] = useState<CropRecommendationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const valid = FIELDS.every((field) => values[field].trim() !== '' && Number.isFinite(Number(values[field])));

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const payload = Object.fromEntries(
        FIELDS.map((field) => [field, Number(values[field])]),
      ) as unknown as CropRecommendationInput;
      setResult(await recommendCrop(payload));
    } catch {
      setError(t('cropRecommendation.error'));
    } finally {
      setLoading(false);
    }
  };

  if (!internalTestFlags.internalFeatureTesting) {
    return <AgScreen><AgText>{t('cropRecommendation.controlledOnly')}</AgText></AgScreen>;
  }

  return (
    <AgScreen scroll keyboardAvoiding contentContainerStyle={styles.content}>
      <AgBadge label={t('cropRecommendation.testMode')} tone="warning" />
      <AgText variant="headingL" weight="bold">{t('cropRecommendation.title')}</AgText>
      <AgText color="muted">{t('cropRecommendation.subtitle')}</AgText>
      <AgCard style={styles.form}>
        {FIELDS.map((field) => (
          <AgInput
            key={field}
            testID={`crop-recommendation-${field}`}
            label={t(`cropRecommendation.fields.${field}`)}
            placeholder={t('cropRecommendation.numberPlaceholder')}
            keyboardType="decimal-pad"
            value={values[field]}
            onChangeText={(value) => setValues((current) => ({ ...current, [field]: value }))}
            required
          />
        ))}
        <AgButton
          title={t('cropRecommendation.submit')}
          onPress={submit}
          disabled={!valid}
          loading={loading}
        />
      </AgCard>
      {error ? <AgText color="danger">{error}</AgText> : null}
      {result ? (
        <AgCard testID="crop-recommendation-result" style={styles.result}>
          <AgText variant="label" color="muted">{t('cropRecommendation.suggested')}</AgText>
          <AgText variant="headingL" weight="bold">{t(`cropRecommendation.crops.${result.recommended_crop}`, { defaultValue: result.recommended_crop })}</AgText>
          <AgText>{t('cropRecommendation.modelProbability', { value: Math.round(result.model_probability * 100) })}</AgText>
          {result.alternatives.length ? (
            <View style={styles.alternatives}>
              <AgText weight="semibold">{t('cropRecommendation.alternatives')}</AgText>
              {result.alternatives.map((item) => (
                <AgText key={item.crop} color="muted">
                  {t(`cropRecommendation.crops.${item.crop}`, { defaultValue: item.crop })} · {Math.round(item.model_probability * 100)}%
                </AgText>
              ))}
            </View>
          ) : null}
          <AgText color="danger" style={styles.disclaimer}>{t('cropRecommendation.disclaimer')}</AgText>
        </AgCard>
      ) : null}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 14, paddingBottom: 32 },
  form: { gap: 14 },
  result: { gap: 8 },
  alternatives: { gap: 4, marginTop: 8 },
  disclaimer: { marginTop: 10 },
});
