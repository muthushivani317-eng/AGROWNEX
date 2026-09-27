import { Alert, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, ArrowRight, CalendarDays, CheckCircle2, ChevronRight, CloudRain, Leaf, MapPin, ShieldCheck, Sprout } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import { AgButton, AgEmptyState, AgErrorState, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { organicActionTitle } from '../actionTitle';
import { useCreateOrganicPractice } from '../hooks/useOrganic';
import { useOrganicPlan } from '../hooks/useOrganicPlan';
import type { OrganicPlanAction, OrganicPlanBundle, OrganicPlanKind } from '../integrationTypes';

const practiceType = (kind: OrganicPlanKind) => kind === 'satellite' ? 'scouting' as const : kind === 'soil' ? 'amendment' as const : kind === 'disease' ? 'biological_treatment' as const : 'custom' as const;
const ACTION_DETAILS: Record<OrganicPlanKind, { icon: typeof Sprout }> = {
  disease: { icon: ShieldCheck }, soil: { icon: Sprout }, calendar: { icon: CalendarDays }, weather: { icon: CloudRain }, satellite: { icon: MapPin },
};

function PlanHeader() {
  const { t } = useTranslation(); const router = useRouter(); const { colors, isDark } = useAppTheme(); const ink = isDark ? colors.text : '#093C29';
  return <><View style={styles.topBar}><TouchableOpacity onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} activeOpacity={0.72} style={[styles.backButton, { backgroundColor: isDark ? '#173322' : '#EAF4E7' }]}><ArrowLeft size={22} color={ink} /></TouchableOpacity><View style={[styles.headerMark, { backgroundColor: isDark ? '#173322' : '#F1F8EF' }]}><Leaf size={17} color={colors.primary} /><AgText variant="caption" weight="bold" style={{ color: colors.primary }}>{t('organic.badge')}</AgText></View></View><View style={styles.heroCopy}><AgText variant="headingL" weight="bold" style={[styles.heroTitle, { color: ink }]}>{t('organic.planTitle')}</AgText><AgText variant="body" style={[styles.heroIntro, { color: colors.textMuted }]}>{t('organic.planIntro')}</AgText></View></>;
}

function PlanSafetyNote() {
  const { t } = useTranslation(); const { colors, isDark } = useAppTheme();
  return <View style={[styles.safetyNote, { backgroundColor: isDark ? '#31270F' : '#FFF7E7', borderColor: isDark ? '#5B481C' : '#F2D9A4' }]}><View style={[styles.safetyIcon, { backgroundColor: isDark ? '#4A3A0E' : '#FEE8B8' }]}><ShieldCheck size={21} color="#C67909" /></View><View style={styles.safetyCopy}><AgText variant="bodySmall" weight="semibold" style={{ color: colors.text }}>{t('organic.checkBeforeApply')}</AgText><AgText variant="caption" style={[styles.safetyBody, { color: colors.textMuted }]}>{t('growth.boost.notice')}</AgText></View></View>;
}

function SourceLine({ action }: { action: OrganicPlanAction }) {
  const { t } = useTranslation(); const { colors, isDark } = useAppTheme(); const verified = action.source.reviewStatus === 'verified' || action.source.reviewStatus === 'sourced_public_reference';
  return <View style={[styles.sourceLine, { borderTopColor: isDark ? '#334438' : '#DFE8DE' }]}><CheckCircle2 size={15} color={verified ? colors.primary : colors.warning} /><AgText variant="caption" numberOfLines={1} style={[styles.sourceText, { color: colors.textMuted }]}>{t(verified ? 'organic.verifiedSource' : 'organic.source', { source: action.source.organization })}</AgText></View>;
}

function ActionCard({ action, farmId }: { action: OrganicPlanAction; farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { colors, isDark } = useAppTheme(); const create = useCreateOrganicPractice(farmId); const detail = ACTION_DETAILS[action.kind]; const Icon = detail.icon; const blocked = action.state === 'waiting_for_weather'; const actionTitle = organicActionTitle(action.title, t);
  const addPractice = () => create.mutate({ type: practiceType(action.kind), title: actionTitle, notes: action.description, occurredAt: new Date().toISOString(), sourceActionId: action.sourceActionId }, { onSuccess: () => Alert.alert(t(action.scoutingOnly ? 'organic.findingRecorded' : 'organic.practiceSaved')) });
  return <View style={[styles.actionCard, { backgroundColor: isDark ? '#1B291F' : '#F2F8F0', borderColor: isDark ? '#38543D' : '#D1E4D0' }]}><View style={styles.actionTopRow}><View style={[styles.kindIcon, { backgroundColor: isDark ? '#25462D' : '#DDF0DA' }]}><Icon size={22} color={colors.primary} /></View><View style={styles.actionMeta}><AgText variant="caption" weight="bold" style={{ color: blocked ? colors.warning : colors.primary }}>{blocked ? t('organic.actionState.waiting_for_weather') : t(`organic.planKindAction.${action.kind}`)}</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>{t(`organic.planKind.${action.kind}`)}</AgText></View>{blocked ? <CloudRain size={20} color={colors.warning} /> : <ChevronRight size={20} color={colors.primary} />}</View><AgText variant="headingS" weight="bold" style={[styles.actionTitle, { color: colors.text }]}>{actionTitle}</AgText>{action.description && action.description !== action.title ? <AgText variant="bodySmall" style={[styles.actionDescription, { color: colors.textMuted }]}>{action.description}</AgText> : null}{action.scoutingOnly ? <View style={styles.scoutingLine}><MapPin size={14} color={colors.info} /><AgText variant="caption" style={{ color: colors.textMuted }}>{t('organic.scoutingOnly')}</AgText></View> : null}<SourceLine action={action} /><AgButton className="mt-4" size="sm" variant={blocked ? 'outline' : 'primary'} title={t(blocked ? 'organic.openCalendarToReschedule' : action.scoutingOnly ? 'organic.recordFinding' : 'organic.addToLogbook')} onPress={blocked ? () => router.push('/calendar' as never) : addPractice} rightIcon={<ArrowRight size={18} color={blocked ? colors.primary : colors.onPrimary} />} /></View>;
}

export function OrganicPlanScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const plan = useOrganicPlan(farmId);
  return <AgScreen scroll contentContainerStyle={styles.screen}><PlanHeader />{plan.isLoading ? <View style={styles.loading}><AgSkeleton className="h-40 w-full" /><AgSkeleton className="mt-3 h-32 w-full" /></View> : plan.isError ? <AgErrorState message={t('organic.planError')} onRetry={() => void plan.refetch()} /> : !plan.data?.actions.length ? <CommonPlanWeek bundle={plan.data} farmId={farmId} /> : <ActionPlan actions={plan.data.actions} farmId={farmId} />}</AgScreen>;
}

function ActionPlan({ actions, farmId }: { actions: OrganicPlanAction[]; farmId: string }) {
  const { t } = useTranslation(); const { colors } = useAppTheme(); const readyCount = actions.filter((action) => action.state !== 'waiting_for_weather').length;
  return <View style={styles.planBody}><View style={styles.sectionHeading}><View><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>{t('organic.thisWeekTitle')}</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>{t('organic.actionsReady', { ready: readyCount, total: actions.length })}</AgText></View><View style={styles.countBadge}><AgText variant="caption" weight="bold" style={styles.countText}>{actions.length}</AgText></View></View><PlanSafetyNote />{actions.map((action) => <ActionCard key={action.id} action={action} farmId={farmId} />)}</View>;
}

/** Shown when no module has produced an action yet: this week's common-plan step(s). */
function CommonPlanWeek({ bundle, farmId }: { bundle: OrganicPlanBundle | undefined; farmId: string }) {
  const { t } = useTranslation(); const router = useRouter(); const { language } = useLanguage(); const { colors, isDark } = useAppTheme(); const ta = language === 'ta'; const steps = bundle?.commonPlan ?? []; const status = bundle?.commonPlanStatus ?? 'needs_sowing_date'; const openPlan = () => router.push(`/organic/conversion-plan?farmId=${farmId}` as never);
  if (!steps.length) return <AgEmptyState title={t('organic.noActions')} message={t(status === 'needs_sowing_date' ? 'organic.planNeedsSowingDate' : 'organic.noStepThisWeek')} actionLabel={t('organic.openConversionPlan')} onAction={openPlan}/>;
  const notice = ta ? bundle?.noticeTa : bundle?.noticeEn;
  return <View style={styles.planBody}><View style={styles.sectionHeading}><View><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>{t('organic.thisWeekTitle')}</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>{t('organic.fieldStepThisWeek')}</AgText></View><View style={styles.countBadge}><Sprout size={16} color="#19723A" /></View></View><PlanSafetyNote />{steps.map((step) => <View key={`${step.cropCycleId}-${step.week}`} style={[styles.actionCard, { backgroundColor: isDark ? '#1B291F' : '#F2F8F0', borderColor: isDark ? '#38543D' : '#D1E4D0' }]}><View style={styles.actionTopRow}><View style={[styles.kindIcon, { backgroundColor: isDark ? '#25462D' : '#DDF0DA' }]}><Sprout size={22} color={colors.primary} /></View><View style={styles.actionMeta}><AgText variant="caption" weight="bold" style={{ color: colors.primary }}>{t('organic.planWeek', { week: step.week })}</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>Crop calendar</AgText></View></View><AgText variant="headingS" weight="bold" style={[styles.actionTitle, { color: colors.text }]}>{ta ? step.titleTa : step.titleEn}</AgText><AgText variant="bodySmall" style={[styles.actionDescription, { color: colors.textMuted }]}>{ta ? step.bodyTa : step.bodyEn}</AgText><AgButton className="mt-4" size="sm" title={t('organic.openConversionPlan')} onPress={openPlan} rightIcon={<ArrowRight size={18} color={colors.onPrimary} />} /></View>)}{notice ? <AgText variant="caption" style={[styles.notice, { color: colors.textMuted }]}>{notice}</AgText> : null}</View>;
}

const styles = StyleSheet.create({
  screen: { paddingTop: 8, paddingBottom: 40 }, topBar: { minHeight: 50, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, backButton: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' }, headerMark: { minHeight: 32, paddingHorizontal: 11, borderRadius: 16, flexDirection: 'row', alignItems: 'center', gap: 6 }, heroCopy: { paddingTop: 24, paddingBottom: 20 }, heroTitle: { letterSpacing: -0.8 }, heroIntro: { marginTop: 7, lineHeight: 23, maxWidth: 390 }, loading: { marginTop: 10 }, planBody: { marginTop: 8 }, sectionHeading: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }, countBadge: { minWidth: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', backgroundColor: '#E6F3E3' }, countText: { color: '#19723A' }, safetyNote: { minHeight: 84, padding: 14, marginBottom: 14, borderRadius: 16, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 12 }, safetyIcon: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' }, safetyCopy: { flex: 1, minWidth: 0 }, safetyBody: { marginTop: 2, lineHeight: 17 }, actionCard: { marginBottom: 14, padding: 17, borderRadius: 20, borderWidth: 1 }, actionTopRow: { flexDirection: 'row', alignItems: 'center' }, kindIcon: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' }, actionMeta: { flex: 1, marginLeft: 11, gap: 1 }, actionTitle: { marginTop: 16, letterSpacing: -0.35 }, actionDescription: { marginTop: 5, lineHeight: 21 }, scoutingLine: { marginTop: 11, flexDirection: 'row', alignItems: 'center', gap: 6 }, sourceLine: { marginTop: 14, paddingTop: 11, borderTopWidth: StyleSheet.hairlineWidth, flexDirection: 'row', alignItems: 'center', gap: 6 }, sourceText: { flex: 1 }, notice: { marginTop: -2, paddingHorizontal: 4, lineHeight: 18 },
});
