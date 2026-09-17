import { useRouter } from 'expo-router';
import {
  ArrowLeft,
  Images,
  MapPin,
  Pencil,
  Sprout,
  Trash2,
  Users,
  Leaf,
  ClipboardList,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

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

function DetailRow({ label, value }: { label: string; value: string | null }) {
  return (
    <View className="flex-row items-start justify-between gap-4 py-2">
      <AgText variant="bodySmall" color="muted">
        {label}
      </AgText>
      <AgText variant="bodySmall" weight="medium" className="flex-1 text-right">
        {value && value.trim() ? value : '—'}
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
    <AgScreen scroll>
      <View className="mt-2 flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="-ml-2 h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold" numberOfLines={1} className="flex-1">
          {farm.name}
        </AgText>
        <AgPressable
          onPress={() => router.push(`/farm/${farmId}/edit`)}
          accessibilityRole="button"
          accessibilityLabel={t('farm.editFarm')}
          className="h-10 w-10 items-center justify-center"
        >
          <Pencil size={20} color={colors.primary} />
        </AgPressable>
      </View>

      <View className="mt-3 flex-row items-center gap-3">
        <FarmStatusBadge status={farm.status} />
        {crop ? (
          <View className="flex-row items-center gap-1.5">
            <Sprout size={14} color={colors.textMuted} />
            <AgText variant="bodySmall" color="muted">
              {crop}
            </AgText>
          </View>
        ) : null}
      </View>

      {/* Map preview */}
      <View className="mt-4">
        <FarmMiniMap boundary={boundary} location={farm.location} />
        <AgButton
          title={t('farm.editBoundary')}
          variant="secondary"
          size="sm"
          className="mt-3"
          leftIcon={<MapPin size={18} color={colors.primary} />}
          onPress={() => router.push(`/farm/${farmId}/boundary`)}
        />
      </View>

      {/* Area */}
      <AgCard className="mt-4">
        <AgText variant="label" color="muted" weight="medium" className="mb-1">
          {t('farm.area')}
        </AgText>
        <AreaSummary hectares={farm.areaHectares} variant="headingS" />
        {boundary?.perimeterM ? (
          <AgText variant="caption" color="muted" className="mt-1">
            {t('farm.perimeter')}: {Math.round(boundary.perimeterM)} {t('farm.metersShort')}
            {boundary.vertexCount ? ` · ${boundary.vertexCount} ${t('farm.points')}` : ''}
          </AgText>
        ) : null}
      </AgCard>

      {/* Details */}
      <AgCard className="mt-4">
        <DetailRow label={t('farm.variety')} value={farm.cropVariety} />
        <View className="h-px bg-border" />
        <DetailRow label={t('farm.sowingDate')} value={farm.sowingDate} />
        <View className="h-px bg-border" />
        <DetailRow
          label={t('farm.soil')}
          value={farm.soilType ? t(`farm.soil${cap(farm.soilType)}`) : null}
        />
        <View className="h-px bg-border" />
        <DetailRow
          label={t('farm.irrigation')}
          value={farm.irrigationType ? t(`farm.irrigation${cap(farm.irrigationType)}`) : null}
        />
        <View className="h-px bg-border" />
        <DetailRow
          label={t('farm.water')}
          value={farm.waterSource ? t(`farm.water${cap(farm.waterSource)}`) : null}
        />
        <View className="h-px bg-border" />
        <DetailRow label={t('farm.district')} value={district} />
        <View className="h-px bg-border" />
        <DetailRow label={t('farm.block')} value={farm.location?.block ?? null} />
        <View className="h-px bg-border" />
        <DetailRow label={t('farm.village')} value={farm.location?.village ?? null} />
      </AgCard>

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

      {organicFeatureEnabled ? <AgCard className="mt-6">
        <View className="flex-row items-center gap-2"><Leaf size={20} color={colors.primary} /><AgText weight="bold">{t('organic.sectionTitle')}</AgText></View>
        <AgText variant="bodySmall" color="muted" className="mt-2">{t('organic.sectionDescription')}</AgText>
        <AgButton className="mt-4" title={t('organic.dashboardTitle')} onPress={() => router.push(`/organic?farmId=${farmId}` as never)} />
        <AgButton className="mt-3" variant="secondary" title={t('organic.profileTitle')} leftIcon={<Leaf size={18} color={colors.primary} />} onPress={() => router.push(`/organic/profile?farmId=${farmId}` as never)} />
        <AgButton className="mt-3" variant="secondary" title={t('organic.logbookTitle')} leftIcon={<ClipboardList size={18} color={colors.primary} />} onPress={() => router.push(`/organic/logbook?farmId=${farmId}` as never)} />
        <AgButton className="mt-3" variant="secondary" title={t('organic.planTitle')} onPress={() => router.push(`/organic/plan?farmId=${farmId}` as never)} />
      </AgCard> : null}

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

/** Capitalize a snake_case enum value for the `farm.<group><Cap>` i18n key. */
function cap(value: string): string {
  const camel = value.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
  return camel.charAt(0).toUpperCase() + camel.slice(1);
}
