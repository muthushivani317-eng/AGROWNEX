import { Alert, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { AgButton, AgCard, AgEmptyState, AgErrorState, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { organicActionTitle } from '../actionTitle';
import { useCreateOrganicPractice } from '../hooks/useOrganic';
import { useOrganicPlan } from '../hooks/useOrganicPlan';
import type { OrganicPlanBundle, OrganicPlanKind } from '../integrationTypes';

const practiceType = (kind: OrganicPlanKind) => kind === 'satellite' ? 'scouting' as const : kind === 'soil' ? 'amendment' as const : kind === 'disease' ? 'biological_treatment' as const : 'custom' as const;
export function OrganicPlanScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors } = useAppTheme(); const plan = useOrganicPlan(farmId); const create = useCreateOrganicPractice(farmId);
  return <AgScreen scroll><View className="flex-row items-center gap-2"><AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} className="h-10 w-10 items-center justify-center"><ArrowLeft size={24} color={colors.text}/></AgPressable><AgText variant="headingM" weight="bold">{t('organic.planTitle')}</AgText></View><AgText color="muted" className="mt-2">{t('organic.planIntro')}</AgText>
  {plan.isLoading ? <><AgSkeleton className="mt-4 h-28 w-full"/><AgSkeleton className="mt-3 h-28 w-full"/></> : plan.isError ? <AgErrorState message={t('organic.planError')} onRetry={() => void plan.refetch()}/> : !plan.data?.actions.length ? <CommonPlanWeek bundle={plan.data} farmId={farmId}/> : plan.data.actions.map((action) => <AgCard key={action.id} className="mt-3"><View className="flex-row justify-between gap-2"><AgText weight="bold" className="flex-1">{organicActionTitle(action.title, t)}</AgText><AgText variant="caption" color="primary">{t(`organic.planKind.${action.kind}`)}</AgText></View>{action.description && action.description !== action.title ? <AgText className="mt-2" variant="bodySmall">{action.description}</AgText> : null}{action.scoutingOnly ? <AgText className="mt-2" variant="caption" color="muted">{t('organic.scoutingOnly')}</AgText> : null}<AgText className="mt-2" variant="caption" color="muted">{t(`organic.actionState.${action.state}`)}</AgText>{action.state === 'waiting_for_weather' ? <AgText className="mt-1" variant="caption" color="muted">{t('organic.weatherNotification')}</AgText> : null}<AgText className="mt-1" variant="caption" color="muted">{action.source.organization} · {action.source.reference}</AgText>{action.state === 'waiting_for_weather' ? <AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.openCalendarToReschedule')} onPress={() => router.push('/calendar' as never)}/> : <AgButton className="mt-3" size="sm" variant="secondary" title={t(action.scoutingOnly ? 'organic.recordFinding' : 'organic.addToLogbook')} onPress={() => create.mutate({ type: practiceType(action.kind), title: organicActionTitle(action.title, t), notes: action.description, occurredAt: new Date().toISOString(), sourceActionId: action.sourceActionId }, { onSuccess: () => Alert.alert(t(action.scoutingOnly ? 'organic.findingRecorded' : 'organic.practiceSaved')) })}/>}</AgCard>)}</AgScreen>;
}

/** Shown when no module has produced an action yet: this week's common-plan step(s). */
function CommonPlanWeek({ bundle, farmId }: { bundle: OrganicPlanBundle | undefined; farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { language } = useLanguage();
  const ta = language === 'ta';
  const steps = bundle?.commonPlan ?? [];
  const status = bundle?.commonPlanStatus ?? 'needs_sowing_date';
  const openPlan = () => router.push(`/organic/conversion-plan?farmId=${farmId}` as never);
  if (!steps.length) {
    return <AgEmptyState title={t('organic.noActions')} message={t(status === 'needs_sowing_date' ? 'organic.planNeedsSowingDate' : 'organic.noStepThisWeek')} actionLabel={t('organic.openConversionPlan')} onAction={openPlan}/>;
  }
  const notice = ta ? bundle?.noticeTa : bundle?.noticeEn;
  return <View className="mt-4">
    <AgText variant="headingS" weight="bold">{t('organic.thisWeekTitle')}</AgText>
    {steps.map((step) => <AgCard key={`${step.cropCycleId}-${step.week}`} className="mt-3">
      <AgText variant="caption" color="primary">{t('organic.planWeek', { week: step.week })}</AgText>
      <AgText weight="bold" className="mt-1">{ta ? step.titleTa : step.titleEn}</AgText>
      <AgText className="mt-2" variant="bodySmall">{ta ? step.bodyTa : step.bodyEn}</AgText>
    </AgCard>)}
    {notice ? <AgText className="mt-3" variant="caption" color="muted">{notice}</AgText> : null}
    <AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.openConversionPlan')} onPress={openPlan}/>
  </View>;
}
