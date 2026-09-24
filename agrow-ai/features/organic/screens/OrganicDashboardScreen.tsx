import { View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, Award, BookOpen, CalendarCheck, ClipboardList, Layers, Leaf } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { AgBadge, AgButton, AgCard, AgErrorState, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { buildOrganicDashboard } from '../organicExperience';
import { useOrganicPractices, useOrganicProfile } from '../hooks/useOrganic';
import { useOrganicPlan } from '../hooks/useOrganicPlan';
import { useOrganicTodayTask } from '../hooks/useOrganicConversion';

export function OrganicDashboardScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors } = useAppTheme(); const { language } = useLanguage(); const profile = useOrganicProfile(farmId); const practices = useOrganicPractices(farmId); const plan = useOrganicPlan(farmId); const todayTask = useOrganicTodayTask(farmId);
  const widgets = buildOrganicDashboard(plan.data?.actions ?? []);
  const firstTask = todayTask.data?.tasks[0];
  const taskTitle = firstTask ? (language === 'ta' ? firstTask.title_ta : (firstTask.title_en ?? firstTask.title_ta)) : null;
  const taskBody = firstTask ? (language === 'ta' ? firstTask.body_ta : (firstTask.body_en ?? firstTask.body_ta)) : null;
  return <AgScreen scroll><View className="flex-row items-center gap-2"><AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} className="h-10 w-10 items-center justify-center"><ArrowLeft size={24} color={colors.text}/></AgPressable><AgText variant="headingM" weight="bold">{t('organic.dashboardTitle')}</AgText></View>
    {firstTask ? <AgCard className="mt-4"><View className="flex-row items-center gap-2"><CalendarCheck size={20} color={colors.primary}/><AgText weight="bold">{t('organic.todayTaskTitle')}</AgText>{firstTask.is_overdue ? <AgBadge label={t('organic.todayTaskOverdue')} tone="warning" /> : null}</View><AgText weight="bold" className="mt-2">{taskTitle}</AgText><AgText variant="bodySmall" color="muted" className="mt-1">{taskBody}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.conversionPlanCta')} onPress={() => router.push(`/organic/conversion-plan?farmId=${farmId}` as never)}/></AgCard> : null}
    <AgCard className="mt-4"><View className="flex-row items-center gap-2"><ClipboardList size={20} color={colors.primary}/><AgText weight="bold">{t('organic.readinessTitle')}</AgText></View><AgText variant="caption" color="muted" className="mt-2">{t('organic.readinessDashboardHint')}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.readinessCta')} onPress={() => router.push(`/organic/readiness?farmId=${farmId}` as never)}/></AgCard>
    <AgCard className="mt-3"><View className="flex-row items-center gap-2"><Layers size={20} color={colors.primary}/><AgText weight="bold">{t('organic.conversionPlanTitle')}</AgText></View><AgText variant="caption" color="muted" className="mt-2">{t('organic.conversionPlanDashboardHint')}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.conversionPlanCta')} onPress={() => router.push(`/organic/conversion-plan?farmId=${farmId}` as never)}/></AgCard>
    <AgCard className="mt-3"><View className="flex-row items-center gap-2"><Leaf size={20} color={colors.primary}/><AgText weight="bold">{profile.data ? t(`organic.mode.${profile.data.mode}.title`) : t('organic.profileNotSet')}</AgText></View><AgText variant="caption" color="muted" className="mt-2">{t('organic.certificationNotice')}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.profileTitle')} onPress={() => router.push(`/organic/profile?farmId=${farmId}` as never)}/></AgCard>
    <AgCard className="mt-3"><View className="flex-row items-center gap-2"><Award size={20} color={colors.primary}/><AgText weight="bold">{t('organic.certificationTitle')}</AgText></View><AgText variant="caption" color="muted" className="mt-2">{t('organic.certificationDashboardHint')}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.certificationCta')} onPress={() => router.push(`/organic/certification?farmId=${farmId}` as never)}/></AgCard>
    <AgCard className="mt-3"><View className="flex-row items-center gap-2"><BookOpen size={20} color={colors.primary}/><AgText weight="bold">{t('organic.logbookTitle')}</AgText></View><AgText className="mt-2">{t('organic.practiceCount', { count: practices.data?.length ?? 0 })}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.openLogbook')} onPress={() => router.push(`/organic/logbook?farmId=${farmId}` as never)}/></AgCard>
    {plan.isLoading ? <AgSkeleton className="mt-3 h-40 w-full"/> : plan.isError ? <AgErrorState message={t('organic.planError')} onRetry={() => void plan.refetch()}/> : widgets.map((widget) => <AgCard key={widget.kind} className="mt-3"><AgText weight="bold">{t(`organic.widget.${widget.kind}`)}</AgText><AgText variant="bodySmall" color="muted" className="mt-1">{t('organic.widgetSummary', { total: widget.total, ready: widget.ready, blocked: widget.blocked })}</AgText></AgCard>)}
    <AgButton className="mt-5" title={t('organic.viewAllActions')} onPress={() => router.push(`/organic/plan?farmId=${farmId}` as never)}/>
    <AgButton className="mt-3" variant="secondary" title={t('organic.inputLibrary')} onPress={() => router.push('/organic/inputs' as never)}/>
  </AgScreen>;
}
