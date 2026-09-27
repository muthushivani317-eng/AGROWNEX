import dayjs from 'dayjs';
import { useRouter } from 'expo-router';
import {
  Activity,
  ArrowLeft,
  Bug,
  CloudSun,
  FlaskConical,
  ListChecks,
  ShieldCheck,
  Sprout,
  Trash2,
  UserCheck,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

import {
  AgBadge,
  AgButton,
  AgCard,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

import { ConfidenceMeter } from '../components/ConfidenceMeter';
import { DiseaseReportImage } from '../components/DiseaseReportImage';
import { InfoList } from '../components/InfoList';
import { SeverityBadge } from '../components/SeverityBadge';
import { applyChemicalPolicy, useChemicalPolicy } from '@/features/organic/chemicalPolicy';
import { useDeleteReport, useDiseaseReport } from '../hooks/useDisease';
import { formatDiagnosisName } from '../utils/diagnosisName';

export function DiseaseDetailScreen({ reportId }: { reportId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language } = useLanguage();

  const { data: report, isLoading, isError, refetch } = useDiseaseReport(reportId);
  const chemicalPolicy = useChemicalPolicy(report?.farmId);
  const del = useDeleteReport();

  if (isLoading) {
    return (
      <AgScreen scroll>
        <AgSkeleton className="h-8 w-40 rounded-md" />
        <AgSkeleton className="mt-4 aspect-square w-full rounded-card" />
        <AgSkeleton className="mt-4 h-40 w-full rounded-card" />
      </AgScreen>
    );
  }

  if (isError || !report) {
    return (
      <AgScreen>
        <AgErrorState onRetry={() => void refetch()} />
      </AgScreen>
    );
  }

  const explanation =
    (language === 'ta' ? report.explanationTamil : report.explanationEnglish) ||
    report.explanationEnglish ||
    report.explanationTamil;

  // Category-level-only conventional (non-organic) guidance -- e.g. "a
  // protectant or systemic fungicide" -- never null for a disease-shaped
  // result and the report just predates this field or was a "healthy"
  // result, both of which correctly render nothing below.
  const conventionalCategory =
    (language === 'ta'
      ? report.conventionalCategoryTamil
      : report.conventionalCategoryEnglish) ||
    report.conventionalCategoryEnglish ||
    report.conventionalCategoryTamil;

  const confirmDelete = () => {
    Alert.alert(t('disease.deleteConfirmTitle'), t('disease.deleteConfirmMessage'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: () =>
          del.mutate(report.id, { onSuccess: () => router.back() }),
      },
    ]);
  };

  return (
    <AgScreen scroll>
      <View style={{ marginTop: 8, flexDirection: 'row', alignItems: 'center' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <AgPressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel={t('common.back')}
            className="-ml-2 h-10 w-10 items-center justify-center"
            style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}
          >
            <ArrowLeft size={24} color={colors.text} />
          </AgPressable>
          <AgText variant="headingM" weight="bold">
            {t('disease.resultTitle')}
          </AgText>
        </View>
      </View>

      {report.privateImageAvailable || report.imageUrl ? (
        <DiseaseReportImage
          reportId={report.id}
          privateImageAvailable={report.privateImageAvailable}
          legacyUrl={report.imageUrl}
          style={{ width: '100%', aspectRatio: 1, borderRadius: 16 }}
          className="mt-3"
        />
      ) : null}

      <View style={{ marginTop: 16, flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <Sprout size={14} color={colors.textMuted} />
        <AgText variant="bodySmall" color="muted">
          {formatDiagnosisName(report.crop) ?? t('disease.cropUnknown')}
          {Number.isFinite(report.cropConfidence)
            ? ` · ${report.cropConfidence}%`
            : ''}
        </AgText>
      </View>

      <AgText variant="headingS" weight="bold" style={{ marginTop: 4 }}>
        {formatDiagnosisName(report.disease) ?? t('disease.cropUnknown')}
      </AgText>

      {report.testMode?.display_required ? (
        <AgCard className="mt-3 border-2 border-danger bg-danger/10">
          <AgText variant="bodySmall" weight="bold" color="danger">
            {report.testMode.banner_text}
          </AgText>
        </AgCard>
      ) : null}

      <View style={{ marginTop: 12, flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <SeverityBadge severity={report.severity} />
        {report.needsExpertReview ? (
          <View className="flex-row items-center gap-1">
            <UserCheck size={14} color={colors.danger} />
            <AgBadge label={t('disease.needsExpert')} tone="danger" />
          </View>
        ) : null}
      </View>

      <View style={{ marginTop: 16 }}>
        <ConfidenceMeter value={report.confidence} />
      </View>

      {explanation ? (
        <AgCard style={{ marginTop: 16, backgroundColor: colors.surface, borderColor: colors.border }}>
          <AgText variant="body">{explanation}</AgText>
        </AgCard>
      ) : null}

      <InfoList icon={Activity} title={t('disease.symptoms')} items={report.symptoms} />
      <InfoList icon={Bug} title={t('disease.causes')} items={report.causes} />
      <InfoList
        icon={ListChecks}
        title={t('disease.recommendations')}
        items={report.recommendations}
      />
      <InfoList
        icon={FlaskConical}
        title={t('disease.conventionalCategory')}
        items={applyChemicalPolicy(conventionalCategory ? [conventionalCategory] : [], chemicalPolicy, t)}
      />
      <InfoList
        icon={ShieldCheck}
        title={t('disease.prevention')}
        items={report.prevention}
      />

      {report.weatherSnapshot?.condition ? (
        <AgCard className="mt-4 flex-row items-center gap-3">
          <CloudSun size={18} color={colors.primary} />
          <AgText variant="bodySmall" color="muted" className="flex-1">
            {t('disease.weatherAtCapture')}:{' '}
            {report.weatherSnapshot.temperatureC != null
              ? `${Math.round(report.weatherSnapshot.temperatureC)}°C · `
              : ''}
            {report.weatherSnapshot.condition}
          </AgText>
        </AgCard>
      ) : null}

      <AgText variant="caption" color="disabled" className="mt-4">
        {t('disease.capturedOn')} {dayjs(report.createdAt).format('YYYY-MM-DD HH:mm')}
      </AgText>

      <AgButton
        variant="danger"
        title={t('disease.deleteReport')}
        onPress={confirmDelete}
        loading={del.isPending}
        leftIcon={<Trash2 size={20} color={colors.onPrimary} />}
        className="mt-6"
      />
    </AgScreen>
  );
}
