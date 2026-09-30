import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  Bug,
  CalendarCheck,
  CalendarDays,
  ChevronRight,
  ClipboardCheck,
  CloudSun,
  Layers3,
  Leaf,
  LibraryBig,
  Satellite,
  ShoppingBasket,
  Sprout,
} from 'lucide-react-native';
import type { ReactNode } from 'react';
import { StyleSheet, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgBadge, AgErrorState, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { AuthLanguageSelector } from '@/features/auth/components/AuthLanguageSelector';
import { useLanguage } from '@/hooks/useLanguage';

import { useOrganicPractices, useOrganicProfile } from '../hooks/useOrganic';
import { useOrganicTodayTask } from '../hooks/useOrganicConversion';
import { useOrganicPlan } from '../hooks/useOrganicPlan';
import type { OrganicPlanKind } from '../integrationTypes';
import { buildOrganicDashboard } from '../organicExperience';

const ORGANIC = {
  background: '#F7F9F3',
  surface: '#FFFDF8',
  ink: '#073F2A',
  muted: '#5E6D65',
  green: '#14723B',
  greenDark: '#0F5D31',
  border: '#DDE5D7',
  mint: '#EAF5E3',
  amber: '#F2A51A',
  amberPale: '#FFF0D2',
};

const ACTION_ICONS: Record<OrganicPlanKind, ReactNode> = {
  disease: <Bug size={25} color={ORGANIC.green} />,
  soil: <Sprout size={25} color={ORGANIC.green} />,
  calendar: <CalendarDays size={25} color={ORGANIC.green} />,
  weather: <CloudSun size={25} color={ORGANIC.amber} />,
  satellite: <Satellite size={25} color="#286AA6" />,
};

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  action: string;
  onPress: () => void;
  tone?: 'green' | 'amber';
  compact: boolean;
}

function FeatureCard({
  icon,
  title,
  description,
  action,
  onPress,
  tone = 'green',
  compact,
}: FeatureCardProps) {
  const primary = tone === 'amber' ? '#A94F00' : ORGANIC.green;
  const iconBackground = tone === 'amber' ? ORGANIC.amberPale : ORGANIC.mint;
  const cardBackground = tone === 'amber' ? '#FFF9EC' : ORGANIC.surface;

  return (
    <TouchableOpacity
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${action}`}
      onPress={onPress}
      activeOpacity={0.76}
      style={[
        styles.featureCard,
        compact && styles.featureCardCompact,
        { backgroundColor: cardBackground },
      ]}
    >
      <View style={styles.featureMain}>
        <View
          style={[
            styles.featureIcon,
            compact && styles.featureIconCompact,
            { backgroundColor: iconBackground },
          ]}
        >
          {icon}
        </View>
        <View style={styles.featureCopy}>
          <AgText variant="body" weight="bold" style={styles.featureTitle}>
            {title}
          </AgText>
          <AgText variant="bodySmall" style={styles.featureDescription}>
            {description}
          </AgText>
        </View>
      </View>
      <View
        style={[
          styles.featureAction,
          compact && styles.featureActionCompact,
          { borderColor: primary },
        ]}
      >
        <AgText
          variant="bodySmall"
          weight="semibold"
          numberOfLines={compact ? 2 : 1}
          style={[styles.featureActionText, { color: primary }]}
        >
          {action}
        </AgText>
        <ArrowRight size={18} color={primary} />
      </View>
    </TouchableOpacity>
  );
}

interface ActionRowProps {
  icon: ReactNode;
  title: string;
  summary: string;
  onPress: () => void;
  isLast: boolean;
}

function ActionRow({ icon, title, summary, onPress, isLast }: ActionRowProps) {
  return (
    <TouchableOpacity
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${summary}`}
      onPress={onPress}
      activeOpacity={0.76}
      style={[styles.actionRow, isLast && styles.actionRowLast]}
    >
      <View style={styles.actionIcon}>{icon}</View>
      <View style={styles.actionCopy}>
        <AgText variant="bodySmall" weight="semibold" style={styles.actionTitle}>
          {title}
        </AgText>
        <AgText variant="caption" style={styles.actionSummary}>
          {summary}
        </AgText>
      </View>
      <ChevronRight size={22} color={ORGANIC.green} />
    </TouchableOpacity>
  );
}

export function OrganicDashboardScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const { language } = useLanguage();
  const profile = useOrganicProfile(farmId);
  const practices = useOrganicPractices(farmId);
  const plan = useOrganicPlan(farmId);
  const todayTask = useOrganicTodayTask(farmId);
  const widgets = buildOrganicDashboard(plan.data?.actions ?? []);
  const firstTask = todayTask.data?.tasks[0];
  const compact = width < 420;
  const taskTitle = firstTask
    ? language === 'ta'
      ? firstTask.title_ta
      : (firstTask.title_en ?? firstTask.title_ta)
    : null;
  const taskBody = firstTask
    ? language === 'ta'
      ? firstTask.body_ta
      : (firstTask.body_en ?? firstTask.body_ta)
    : null;
  const openPlan = () => router.push(`/organic/plan?farmId=${farmId}` as never);

  return (
    <AgScreen
      testID="organic-dashboard-screen"
      scroll
      padded={false}
      backgroundColor={ORGANIC.background}
      contentContainerStyle={styles.screen}
    >
      <View style={[styles.header, compact && styles.headerCompact]}>
        <TouchableOpacity
          onPress={() => router.back()}
          activeOpacity={0.72}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          style={[styles.backButton, compact && styles.backButtonCompact]}
        >
          <ArrowLeft size={24} color={ORGANIC.greenDark} />
        </TouchableOpacity>

        <View style={styles.brand} accessible accessibilityLabel="AgrowNex">
          <Image
            source={require('@/assets/images/android-icon-foreground.png')}
            contentFit="contain"
            style={[styles.brandMark, compact && styles.brandMarkCompact]}
            accessible={false}
          />
          <View style={styles.brandWords}>
            <AgText variant="headingS" weight="bold" style={[styles.brandAgrow, compact && styles.brandWordCompact]}>
              Agrow
            </AgText>
            <AgText variant="headingS" weight="bold" style={[styles.brandNex, compact && styles.brandWordCompact]}>
              Nex
            </AgText>
          </View>
        </View>

        <AuthLanguageSelector
          variant="hero"
          compact={compact}
          style={compact ? styles.languageSelectorCompact : styles.languageSelector}
        />
      </View>

      <View style={styles.hero}>
        <Image
          source={require('@/assets/images/organic-dashboard-landscape.png')}
          contentFit="cover"
          contentPosition="bottom"
          style={styles.heroLandscape}
          accessible={false}
        />
        <View style={styles.heroCopy}>
          <AgText variant="headingL" weight="bold" style={styles.heroTitle}>
            {t('organic.dashboardTitle')}
          </AgText>
          <AgText variant="body" style={styles.heroSubtitle}>
            {t('organic.dashboardSubtitle')}
          </AgText>
        </View>
      </View>

      <View style={styles.content}>
        {firstTask ? (
          <View style={styles.todayCard}>
            <View style={styles.todayHeader}>
              <View style={styles.todayIcon}>
                <CalendarCheck size={22} color={ORGANIC.green} />
              </View>
              <AgText variant="bodySmall" weight="bold" style={styles.todayLabel}>
                {t('organic.todayTaskTitle')}
              </AgText>
              {firstTask.is_overdue ? (
                <AgBadge label={t('organic.todayTaskOverdue')} tone="warning" />
              ) : null}
            </View>
            <AgText variant="body" weight="bold" style={styles.todayTitle}>
              {taskTitle}
            </AgText>
            <AgText variant="bodySmall" style={styles.todayBody}>
              {taskBody}
            </AgText>
            <TouchableOpacity
              accessibilityRole="button"
              onPress={() => router.push(`/organic/conversion-plan?farmId=${farmId}` as never)}
              activeOpacity={0.76}
              style={styles.todayAction}
            >
              <AgText variant="bodySmall" weight="semibold" style={styles.todayActionText}>
                {t('organic.conversionPlanDashboardCta')}
              </AgText>
              <ArrowRight size={18} color={ORGANIC.green} />
            </TouchableOpacity>
          </View>
        ) : null}

        <FeatureCard
          compact={compact}
          icon={<ClipboardCheck size={31} color={ORGANIC.green} />}
          title={t('organic.readinessTitle')}
          description={t('organic.readinessDashboardHint')}
          action={t('organic.readinessDashboardCta')}
          onPress={() => router.push(`/organic/readiness?farmId=${farmId}` as never)}
        />
        <FeatureCard
          compact={compact}
          tone="amber"
          icon={<Layers3 size={31} color={ORGANIC.green} />}
          title={t('organic.conversionPlanTitle')}
          description={t('organic.conversionPlanDashboardHint')}
          action={t('organic.conversionPlanDashboardCta')}
          onPress={() => router.push(`/organic/conversion-plan?farmId=${farmId}` as never)}
        />
        <FeatureCard
          compact={compact}
          icon={<Leaf size={31} color={ORGANIC.green} />}
          title={
            profile.data
              ? t(`organic.mode.${profile.data.mode}.title`)
              : t('organic.profileNotSet')
          }
          description={t('organic.certificationNotice')}
          action={t('organic.profileDashboardCta')}
          onPress={() => router.push(`/organic/profile?farmId=${farmId}` as never)}
        />
        <FeatureCard
          compact={compact}
          icon={<Award size={31} color={ORGANIC.green} />}
          title={t('organic.certificationTitle')}
          description={t('organic.certificationDashboardHint')}
          action={t('organic.certificationDashboardCta')}
          onPress={() => router.push(`/organic/certification?farmId=${farmId}` as never)}
        />
        <FeatureCard
          compact={compact}
          tone="amber"
          icon={<BookOpen size={31} color={ORGANIC.green} />}
          title={t('organic.logbookTitle')}
          description={t('organic.practiceCount', { count: practices.data?.length ?? 0 })}
          action={t('organic.logbookDashboardCta')}
          onPress={() => router.push(`/organic/logbook?farmId=${farmId}` as never)}
        />
        <FeatureCard
          compact={compact}
          icon={<ShoppingBasket size={31} color={ORGANIC.green} />}
          title={t('organic.marketLinkTitle')}
          description={t('organic.marketLinkDescription')}
          action={t('organic.marketLinkDashboardCta')}
          onPress={() => router.push('/produce?organicOnly=true' as never)}
        />

        <View style={styles.actionGroup}>
          {plan.isLoading ? (
            <>
              <AgSkeleton style={styles.actionSkeleton} />
              <AgSkeleton style={styles.actionSkeleton} />
              <AgSkeleton style={styles.actionSkeleton} />
            </>
          ) : plan.isError ? (
            <View style={styles.errorState}>
              <AgErrorState light message={t('organic.planError')} onRetry={() => void plan.refetch()} />
            </View>
          ) : (
            widgets.map((widget, index) => (
              <ActionRow
                key={widget.kind}
                icon={ACTION_ICONS[widget.kind]}
                title={t(`organic.widget.${widget.kind}`)}
                summary={t('organic.widgetSummary', {
                  total: widget.total,
                  ready: widget.ready,
                  blocked: widget.blocked,
                })}
                onPress={openPlan}
                isLast={index === widgets.length - 1}
              />
            ))
          )}
        </View>

        <TouchableOpacity
          accessibilityRole="button"
          onPress={openPlan}
          activeOpacity={0.76}
          style={styles.primaryAction}
        >
          <AgText variant="body" weight="bold" style={styles.primaryActionText}>
            {t('organic.viewAllActions')}
          </AgText>
          <ArrowRight size={21} color="#FFFFFF" />
        </TouchableOpacity>

        <TouchableOpacity
          accessibilityRole="button"
          onPress={() => router.push('/organic/inputs' as never)}
          activeOpacity={0.76}
          style={styles.libraryAction}
        >
          <LibraryBig size={24} color={ORGANIC.green} />
          <AgText variant="body" weight="semibold" style={styles.libraryText}>
            {t('organic.inputLibrary')}
          </AgText>
          <ChevronRight size={22} color={ORGANIC.green} />
        </TouchableOpacity>
      </View>

      <Image
        source={require('@/assets/images/organic-dashboard-landscape.png')}
        contentFit="cover"
        contentPosition="bottom"
        style={styles.footerLandscape}
        accessible={false}
      />
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 0 },
  header: {
    minHeight: 76,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 6,
  },
  headerCompact: { minHeight: 68, paddingHorizontal: 10, gap: 2 },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F0F5E8',
  },
  backButtonCompact: { width: 44, height: 44, borderRadius: 22 },
  brand: { minWidth: 0, flexShrink: 1, flexDirection: 'row', alignItems: 'center' },
  brandMark: { width: 46, height: 46 },
  brandMarkCompact: { width: 38, height: 38 },
  brandWords: { marginLeft: -5, flexDirection: 'row', alignItems: 'baseline' },
  brandAgrow: { color: ORGANIC.greenDark, letterSpacing: -0.7 },
  brandNex: { color: '#E78312', letterSpacing: -0.7 },
  brandWordCompact: { fontSize: 18, lineHeight: 24 },
  languageSelector: { flexShrink: 0 },
  languageSelectorCompact: { flexShrink: 0 },
  hero: { height: 184, overflow: 'hidden' },
  heroLandscape: { position: 'absolute', right: 0, bottom: 0, left: 0, height: 120 },
  heroCopy: { paddingHorizontal: 20, paddingTop: 12, maxWidth: 430 },
  heroTitle: { color: ORGANIC.ink, letterSpacing: -0.7 },
  heroSubtitle: { maxWidth: 360, marginTop: 4, color: ORGANIC.muted, lineHeight: 22 },
  content: { paddingHorizontal: 16, paddingTop: 14 },
  todayCard: {
    marginBottom: 12,
    padding: 18,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#D2E3CB',
    backgroundColor: '#EFF8E9',
  },
  todayHeader: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  todayIcon: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  todayLabel: { flex: 1, color: ORGANIC.green },
  todayTitle: { marginTop: 12, color: ORGANIC.ink },
  todayBody: { marginTop: 3, color: ORGANIC.muted },
  todayAction: {
    minHeight: 44,
    marginTop: 10,
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  todayActionText: { color: ORGANIC.green },
  featureCard: {
    minHeight: 120,
    marginBottom: 16,
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#CBD8C7',
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#355F3E',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 3,
  },
  featureCardCompact: { alignItems: 'stretch', flexDirection: 'column' },
  featureMain: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  featureIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureIconCompact: { width: 52, height: 52, borderRadius: 26 },
  featureCopy: { flex: 1, minWidth: 0, marginLeft: 14, marginRight: 12 },
  featureTitle: { color: ORGANIC.ink, lineHeight: 21 },
  featureDescription: { marginTop: 4, color: ORGANIC.muted, lineHeight: 19 },
  featureAction: {
    minWidth: 128,
    minHeight: 48,
    paddingHorizontal: 16,
    borderRadius: 24,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: 'rgba(255,255,255,0.72)',
  },
  featureActionCompact: {
    minWidth: 0,
    marginTop: 12,
    marginLeft: 66,
    paddingHorizontal: 14,
    alignSelf: 'stretch',
  },
  featureActionText: { flexShrink: 1, textAlign: 'center' },
  actionGroup: {
    marginTop: 4,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: ORGANIC.border,
    overflow: 'hidden',
    backgroundColor: ORGANIC.surface,
  },
  actionRow: {
    minHeight: 76,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#D9E1D5',
  },
  actionRowLast: { borderBottomWidth: 0 },
  actionIcon: { width: 44, alignItems: 'flex-start', justifyContent: 'center' },
  actionCopy: { flex: 1, minWidth: 0, marginRight: 10 },
  actionTitle: { color: ORGANIC.ink },
  actionSummary: { marginTop: 2, color: ORGANIC.muted },
  actionSkeleton: { height: 76, margin: 8, borderRadius: 14 },
  errorState: { paddingVertical: 12 },
  primaryAction: {
    minHeight: 58,
    marginTop: 14,
    paddingHorizontal: 24,
    borderRadius: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    backgroundColor: ORGANIC.green,
  },
  primaryActionText: { color: '#FFFFFF' },
  libraryAction: {
    minHeight: 64,
    marginTop: 12,
    paddingHorizontal: 20,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: ORGANIC.border,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: ORGANIC.surface,
  },
  libraryText: { flex: 1, color: ORGANIC.ink },
  footerLandscape: { width: '100%', height: 116, marginTop: 4 },
});
