import { View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, BookOpen, Leaf } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { AgButton, AgCard, AgErrorState, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { buildOrganicDashboard } from '../organicExperience';
import { useOrganicPractices, useOrganicProfile } from '../hooks/useOrganic';
import { useOrganicPlan } from '../hooks/useOrganicPlan';

export function OrganicDashboardScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors } = useAppTheme(); const profile = useOrganicProfile(farmId); const practices = useOrganicPractices(farmId); const plan = useOrganicPlan(farmId);
  const widgets = buildOrganicDashboard(plan.data?.actions ?? []);
  return <AgScreen scroll><View className="flex-row items-center gap-2"><AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} className="h-10 w-10 items-center justify-center"><ArrowLeft size={24} color={colors.text}/></AgPressable><AgText variant="headingM" weight="bold">{t('organic.dashboardTitle')}</AgText></View>
    <AgCard className="mt-4"><View className="flex-row items-center gap-2"><Leaf size={20} color={colors.primary}/><AgText weight="bold">{profile.data ? t(`organic.mode.${profile.data.mode}.title`) : t('organic.profileNotSet')}</AgText></View><AgText variant="caption" color="muted" className="mt-2">{t('organic.certificationNotice')}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.profileTitle')} onPress={() => router.push(`/organic/profile?farmId=${farmId}` as never)}/></AgCard>
    <AgCard className="mt-3"><View className="flex-row items-center gap-2"><BookOpen size={20} color={colors.primary}/><AgText weight="bold">{t('organic.logbookTitle')}</AgText></View><AgText className="mt-2">{t('organic.practiceCount', { count: practices.data?.length ?? 0 })}</AgText><AgButton className="mt-3" size="sm" variant="secondary" title={t('organic.openLogbook')} onPress={() => router.push(`/organic/logbook?farmId=${farmId}` as never)}/></AgCard>
    {plan.isLoading ? <AgSkeleton className="mt-3 h-40 w-full"/> : plan.isError ? <AgErrorState message={t('organic.planError')} onRetry={() => void plan.refetch()}/> : widgets.map((widget) => <AgCard key={widget.kind} className="mt-3"><AgText weight="bold">{t(`organic.widget.${widget.kind}`)}</AgText><AgText variant="bodySmall" color="muted" className="mt-1">{t('organic.widgetSummary', { total: widget.total, ready: widget.ready, blocked: widget.blocked })}</AgText></AgCard>)}
    <AgButton className="mt-5" title={t('organic.viewAllActions')} onPress={() => router.push(`/organic/plan?farmId=${farmId}` as never)}/>
    <AgButton className="mt-3" variant="secondary" title={t('organic.inputLibrary')} onPress={() => router.push('/organic/inputs' as never)}/>
  </AgScreen>;
}
