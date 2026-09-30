import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import {
  ArrowLeft,
  BarChart3,
  CalendarDays,
  ChevronRight,
  Droplets,
  Images,
  MapPin,
  MoreVertical,
  Ruler,
  Sprout,
  Trash2,
  Users,
  Leaf,
  Target,
  ClipboardList,
  Waves,
} from 'lucide-react-native';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, TouchableOpacity, View } from 'react-native';

import {
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
import { internalTestFlags } from '@/config/internalTestFlags';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';

import { AreaSummary } from '../components/AreaSummary';
import { FarmImageGallery } from '../components/FarmImageGallery';
import { FarmMiniMap } from '../components/FarmMiniMap';
import { FarmStatusBadge } from '../components/FarmStatusBadge';
import { useFarm } from '../hooks/useFarms';
import { useDeleteFarm } from '../hooks/useFarmMutations';
import { cropLabel, districtLabel } from '../utils/labels';

const FARM_DETAIL_COLORS = {
  canvas: '#F7F7EF',
  surface: '#FFFDF8',
  ink: '#073F2A',
  muted: '#66716B',
  green: '#16833B',
  paleGreen: '#EAF5E7',
  border: '#E0E5DA',
};

function DetailRow({
  icon,
  label,
  value,
  isLast = false,
}: {
  icon: ReactNode;
  label: string;
  value: string | null;
  isLast?: boolean;
}) {
  return (
    <View style={[styles.detailRow, !isLast && styles.detailRowBorder]}>
      <View style={styles.detailIcon}>{icon}</View>
      <AgText variant="bodySmall" style={styles.detailLabel}>{label}</AgText>
      <AgText variant="bodySmall" weight="medium" style={styles.detailValue}>
        {value && value.trim() ? value : '-'}
      </AgText>
    </View>
  );
}

export function FarmDetailsScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { isTamil } = useLanguage();

  const { data: farm, isLoading, isError, refetch } = useFarm(farmId);
  const del = useDeleteFarm();

  if (isLoading) {
    return (
      <AgScreen scroll>
        <AgSkeleton className="h-8 w-40 rounded-md" />
        <AgSkeleton className="mt-4 h-48 w-full rounded-card" />
        <AgSkeleton className="mt-4 h-40 w-full rounded-card" />
      </AgScreen>
    );
  }

  if (isError || !farm) {
    return (
      <AgScreen>
        <AgErrorState
          message={t('farm.errorNotFound')}
          onRetry={() => void refetch()}
        />
      </AgScreen>
    );
  }

  const confirmDelete = () => {
    Alert.alert(t('farm.deleteConfirmTitle'), t('farm.deleteConfirmMsg'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: () =>
          del.mutate(farmId, {
            onSuccess: () => {
              Alert.alert(t('farm.deleted'));
              router.back();
            },
            onError: () => Alert.alert(t('errors.generic')),
          }),
      },
    ]);
  };

  const crop = cropLabel(farm.crop, isTamil);
  const district = districtLabel(farm.location?.district ?? null, isTamil);
  const boundary = farm.boundary;

  return (
    <AgScreen
      scroll
      padded={false}
      backgroundColor={FARM_DETAIL_COLORS.canvas}
      contentContainerStyle={styles.screen}
    >
      <View style={styles.headerBar}>
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          style={styles.headerButton}
        >
          <ArrowLeft size={26} color={FARM_DETAIL_COLORS.ink} />
        </AgPressable>

        <View style={styles.brand} accessible accessibilityLabel="AgrowNex">
          <Image
            source={require('@/assets/images/android-icon-foreground.png')}
            contentFit="contain"
            transition={0}
            style={styles.brandLogo}
            accessible={false}
          />
          <View style={styles.brandWordmark}>
            <AgText variant="headingS" weight="bold" style={styles.brandAgrow}>Agrow</AgText>
            <AgText variant="headingS" weight="bold" style={styles.brandNex}>Nex</AgText>
          </View>
        </View>

        <AgPressable
          onPress={() => router.push(`/farm/${farmId}/edit`)}
          accessibilityRole="button"
          accessibilityLabel={t('farm.editFarm')}
          style={styles.headerButton}
        >
          <MoreVertical size={25} color={FARM_DETAIL_COLORS.ink} />
        </AgPressable>
      </View>

      <View style={styles.farmIdentity}>
        <AgText variant="headingXL" weight="bold" numberOfLines={2} style={styles.farmName}>
          {farm.name}
        </AgText>
        <View style={styles.identityMeta}>
          <FarmStatusBadge status={farm.status} />
          {crop ? (
            <View style={styles.cropMeta}>
              <Sprout size={22} color={FARM_DETAIL_COLORS.green} />
              <AgText variant="body" style={styles.cropText}>{crop}</AgText>
            </View>
          ) : null}
        </View>
      </View>

      {/* Map preview */}
      <View style={styles.mapCard}>
        <FarmMiniMap boundary={boundary} location={farm.location} height={300} />
        <AgButton
          title={t('farm.editBoundary')}
          variant="outline"
          size="lg"
          className="mt-3"
          leftIcon={<MapPin size={20} color={colors.primary} />}
          rightIcon={<ChevronRight size={20} color={colors.primary} />}
          onPress={() => router.push(`/farm/${farmId}/boundary`)}
        />
      </View>

      {/* Area */}
      <View style={styles.areaCard}>
        <View style={styles.areaIcon}>
          <Ruler size={30} color={FARM_DETAIL_COLORS.green} />
        </View>
        <View style={styles.areaCopy}>
          <AgText variant="bodySmall" style={styles.areaLabel}>{t('farm.area')}</AgText>
          <AreaSummary hectares={farm.areaHectares} variant="headingL" />
          {boundary?.perimeterM ? (
            <AgText variant="bodySmall" style={styles.areaMeta}>
              {t('farm.perimeter')}: {Math.round(boundary.perimeterM)} {t('farm.metersShort')}
              {boundary.vertexCount ? ` · ${boundary.vertexCount} ${t('farm.points')}` : ''}
            </AgText>
          ) : null}
        </View>
      </View>

      {/* Details */}
      <View style={styles.detailsCard}>
        <View style={styles.detailsHeading}>
          <View style={styles.sectionIcon}>
            <ClipboardList size={21} color={FARM_DETAIL_COLORS.green} />
          </View>
          <AgText variant="headingS" weight="bold" style={styles.detailsTitle}>
            {t('farm.detailsTitle')}
          </AgText>
        </View>
        <DetailRow icon={<Leaf size={17} color={FARM_DETAIL_COLORS.green} />} label={t('farm.variety')} value={farm.cropVariety} />
        <DetailRow icon={<CalendarDays size={17} color={FARM_DETAIL_COLORS.green} />} label={t('farm.sowingDate')} value={farm.sowingDate} />
        <DetailRow
          icon={<Sprout size={17} color={FARM_DETAIL_COLORS.green} />}
          label={t('farm.soil')}
          value={farm.soilType ? t(`farm.soil${cap(farm.soilType)}`) : null}
        />
        <DetailRow
          icon={<Droplets size={17} color={FARM_DETAIL_COLORS.green} />}
          label={t('farm.irrigation')}
          value={farm.irrigationType ? t(`farm.irrigation${cap(farm.irrigationType)}`) : null}
        />
        <DetailRow
          icon={<Waves size={17} color={FARM_DETAIL_COLORS.green} />}
          label={t('farm.water')}
          value={farm.waterSource ? t(`farm.water${cap(farm.waterSource)}`) : null}
        />
        <DetailRow icon={<MapPin size={17} color={FARM_DETAIL_COLORS.green} />} label={t('farm.district')} value={district} />
        <DetailRow icon={<MapPin size={17} color={FARM_DETAIL_COLORS.green} />} label={t('farm.block')} value={farm.location?.block ?? null} />
        <DetailRow icon={<MapPin size={17} color={FARM_DETAIL_COLORS.green} />} label={t('farm.village')} value={farm.location?.village ?? null} isLast />
      </View>

      {farm.notes ? (
        <AgCard className="mt-4">
          <AgText variant="label" color="muted" weight="medium" className="mb-1">
            {t('farm.notes')}
          </AgText>
          <AgText variant="body">{farm.notes}</AgText>
        </AgCard>
      ) : null}

      {/* Photos */}
      <View className="mt-4">
        <View className="mb-2 flex-row items-center justify-between">
          <AgText variant="label" color="muted" weight="medium">
            {t('farm.photos')}
          </AgText>
          <AgPressable
            onPress={() => router.push(`/farm/${farmId}/gallery`)}
            accessibilityRole="button"
            accessibilityLabel={t('farm.viewGallery')}
            className="flex-row items-center gap-1"
          >
            <Images size={16} color={colors.primary} />
            <AgText variant="bodySmall" weight="medium" color="primary">
              {t('farm.viewGallery')}
            </AgText>
          </AgPressable>
        </View>
        {farm.images.length ? (
          <FarmImageGallery images={farm.images.slice(0, 6)} />
        ) : (
          <AgText variant="bodySmall" color="muted">
            {t('farm.noImages')}
          </AgText>
        )}
      </View>

      {internalTestFlags.internalFeatureTesting ? (
        <AgButton
          title={t('farmTeam.manage')}
          variant="secondary"
          leftIcon={<Users size={20} color={colors.primary} />}
          onPress={() => router.push(`/farm/${farmId}/team`)}
          className="mt-6"
        />
      ) : null}

      {organicFeatureEnabled ? <OrganicFarmHub farmId={farmId} /> : null}

      <AgButton
        variant="danger"
        title={t('farm.deleteFarm')}
        onPress={confirmDelete}
        loading={del.isPending}
        leftIcon={<Trash2 size={20} color="#fff" />}
        className="mt-8"
      />
    </AgScreen>
  );
}

function OrganicFarmHub({ farmId }: { farmId: string }) {
  const { t } = useTranslation(); const router = useRouter();
  const actions = [
    { title: t('organic.profileTitle'), body: 'Plan your organic farming approach and set goals.', icon: ClipboardList, tone: 'green', route: `/organic/profile?farmId=${farmId}` },
    { title: t('organic.logbookTitle'), body: 'Keep a private record of your organic practices.', icon: CalendarDays, tone: 'amber', route: `/organic/logbook?farmId=${farmId}` },
    { title: t('organic.planTitle'), body: 'Track actions and stay on course towards your goals.', icon: Target, tone: 'mint', route: `/organic/plan?farmId=${farmId}` },
  ] as const;
  return <View style={styles.organicHub}><View style={styles.organicHero}><Image source={require('@/assets/images/organic-dashboard-landscape.png')} contentFit="cover" contentPosition="right bottom" style={styles.organicLandscape} accessible={false} /><View style={styles.organicHeroCopy}><View style={styles.organicLeafIcon}><Leaf size={34} color={FARM_DETAIL_COLORS.green} /></View><AgText variant="headingL" weight="bold" style={styles.organicHeroTitle}>{t('organic.sectionTitle')}</AgText><AgText variant="body" style={styles.organicHeroBody}>{t('organic.sectionDescription')}</AgText></View></View><TouchableOpacity onPress={() => router.push(`/organic?farmId=${farmId}` as never)} accessibilityRole="button" accessibilityLabel={t('organic.dashboardTitle')} activeOpacity={0.8} style={styles.organicDashboardShell}><View style={[styles.organicDashboard, styles.forceRow, { backgroundColor: '#087735' }]}><View style={styles.organicDashboardIcon}><BarChart3 size={28} color="#FFFFFF" /></View><AgText variant="bodyLarge" weight="bold" style={styles.organicDashboardText}>{t('organic.dashboardTitle')}</AgText><ChevronRight size={29} color="#FFFFFF" style={styles.organicChevron} /></View></TouchableOpacity>{actions.map((action) => { const Icon = action.icon; const iconStyle = action.tone === 'amber' ? styles.organicActionAmber : action.tone === 'mint' ? styles.organicActionMint : styles.organicActionGreen; return <TouchableOpacity key={action.title} onPress={() => router.push(action.route as never)} accessibilityRole="button" accessibilityLabel={action.title} activeOpacity={0.8} style={styles.organicActionShell}><View style={[styles.organicAction, styles.forceRow, { backgroundColor: FARM_DETAIL_COLORS.surface }]}><View style={[styles.organicActionIcon, iconStyle]}><Icon size={29} color={action.tone === 'amber' ? '#B46512' : FARM_DETAIL_COLORS.green} /></View><View style={styles.organicActionCopy}><AgText variant="headingS" weight="bold" style={styles.organicActionTitle}>{action.title}</AgText><AgText variant="bodySmall" style={styles.organicActionBody}>{action.body}</AgText></View><ChevronRight size={24} color={FARM_DETAIL_COLORS.green} style={styles.organicChevron} /></View></TouchableOpacity>; })}</View>;
}

/** Capitalize a snake_case enum value for the `farm.<group><Cap>` i18n key. */
function cap(value: string): string {
  const camel = value.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
  return camel.charAt(0).toUpperCase() + camel.slice(1);
}

const styles = StyleSheet.create({
  screen: { paddingHorizontal: 20, paddingBottom: 36 },
  headerBar: {
    minHeight: 70,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: FARM_DETAIL_COLORS.paleGreen,
  },
  brand: { flexDirection: 'row', alignItems: 'center' },
  brandLogo: { width: 46, height: 46 },
  brandWordmark: { marginLeft: -5, flexDirection: 'row', alignItems: 'baseline' },
  brandAgrow: { color: FARM_DETAIL_COLORS.ink, letterSpacing: -0.8 },
  brandNex: { color: FARM_DETAIL_COLORS.ink, letterSpacing: -0.8 },
  farmIdentity: { marginTop: 22, marginBottom: 18 },
  farmName: { color: FARM_DETAIL_COLORS.ink, fontSize: 38, lineHeight: 44 },
  identityMeta: { marginTop: 12, flexDirection: 'row', alignItems: 'center', gap: 18 },
  cropMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cropText: { color: FARM_DETAIL_COLORS.muted },
  mapCard: {
    padding: 10,
    paddingBottom: 12,
    borderRadius: 28,
    borderWidth: 1,
    borderColor: FARM_DETAIL_COLORS.border,
    backgroundColor: FARM_DETAIL_COLORS.surface,
    shadowColor: '#345C42',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.1,
    shadowRadius: 18,
    elevation: 3,
  },
  areaCard: {
    marginTop: 18,
    padding: 20,
    borderRadius: 24,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: FARM_DETAIL_COLORS.surface,
    borderWidth: 1,
    borderColor: FARM_DETAIL_COLORS.border,
  },
  areaIcon: {
    width: 62,
    height: 62,
    marginRight: 16,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: FARM_DETAIL_COLORS.paleGreen,
  },
  areaCopy: { flex: 1 },
  areaLabel: { color: FARM_DETAIL_COLORS.muted, marginBottom: 2 },
  areaMeta: { color: FARM_DETAIL_COLORS.muted, marginTop: 3 },
  detailsCard: {
    marginTop: 18,
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 8,
    borderRadius: 24,
    backgroundColor: FARM_DETAIL_COLORS.surface,
    borderWidth: 1,
    borderColor: FARM_DETAIL_COLORS.border,
  },
  detailsHeading: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  sectionIcon: {
    width: 42,
    height: 42,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: FARM_DETAIL_COLORS.paleGreen,
  },
  detailsTitle: { marginLeft: 12, color: FARM_DETAIL_COLORS.ink },
  detailRow: { minHeight: 54, flexDirection: 'row', alignItems: 'center' },
  detailRowBorder: { borderBottomWidth: 1, borderBottomColor: '#E8EBE4' },
  detailIcon: {
    width: 34,
    height: 34,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F0F6ED',
  },
  detailLabel: { width: '34%', marginLeft: 10, color: FARM_DETAIL_COLORS.muted },
  detailValue: { flex: 1, color: FARM_DETAIL_COLORS.ink },
  organicHub: { marginTop: 24, padding: 12, borderRadius: 28, backgroundColor: '#F3F8EF', borderWidth: 1, borderColor: '#DFE9DB' },
  organicHero: { minHeight: 236, overflow: 'hidden', borderRadius: 22, backgroundColor: FARM_DETAIL_COLORS.surface },
  organicLandscape: { position: 'absolute', right: -20, bottom: 0, width: '82%', height: '66%', opacity: 0.58 },
  organicHeroCopy: { padding: 21, maxWidth: '76%' },
  organicLeafIcon: { width: 84, height: 84, borderRadius: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#E4F2DD' },
  organicHeroTitle: { marginTop: 18, color: FARM_DETAIL_COLORS.ink, letterSpacing: -0.7 },
  organicHeroBody: { marginTop: 8, color: FARM_DETAIL_COLORS.muted, lineHeight: 24 },
  organicDashboardShell: { marginTop: 12, borderRadius: 24, overflow: 'hidden' },
  forceRow: { width: '100%', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-start' },
  organicDashboard: { minHeight: 86, paddingHorizontal: 19, backgroundColor: '#087735', flexDirection: 'row', alignItems: 'center', gap: 13 },
  organicDashboardIcon: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center', backgroundColor: '#07632E' },
  organicDashboardText: { flex: 1, color: '#FFFFFF' },
  organicChevron: { flexShrink: 0 },
  organicActionShell: { marginTop: 12, borderRadius: 22, overflow: 'hidden', shadowColor: '#31593A', shadowOpacity: 0.08, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  organicAction: { minHeight: 112, padding: 16, backgroundColor: FARM_DETAIL_COLORS.surface, flexDirection: 'row', alignItems: 'center', gap: 14 },
  organicActionIcon: { width: 72, height: 72, borderRadius: 21, alignItems: 'center', justifyContent: 'center' },
  organicActionGreen: { backgroundColor: '#E9F5E4' },
  organicActionAmber: { backgroundColor: '#FFF3DF' },
  organicActionMint: { backgroundColor: '#E0F5E9' },
  organicActionCopy: { flex: 1, minWidth: 0 },
  organicActionTitle: { color: FARM_DETAIL_COLORS.ink, letterSpacing: -0.35 },
  organicActionBody: { marginTop: 4, color: FARM_DETAIL_COLORS.muted, lineHeight: 20 },
});
