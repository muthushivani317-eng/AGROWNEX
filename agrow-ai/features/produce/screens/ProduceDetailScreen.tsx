import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import {
  Camera,
  CalendarClock,
  History as HistoryIcon,
  MapPin,
  Pencil,
  ShieldCheck,
  Sprout,
  Trash2,
  TrendingUp,
  Route,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, ScrollView, View } from 'react-native';

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
import { uploadService } from '@/features/profile/services/uploadProvider';
import { useAppTheme } from '@/hooks/useAppTheme';
import { internalTestFlags } from '@/config/internalTestFlags';
import { capturePhoto, pickPhoto } from '@/utils/image';

import { HarvestWindowBadge } from '../components/HarvestWindowBadge';
import { ProduceBackHeader } from '../components/ProduceBackHeader';
import { ProduceStatusBadge } from '../components/ProduceStatusBadge';
import { BuyerOfferApprovalCard } from '../components/BuyerOfferApprovalCard';
import {
  GRADE_LABEL_KEY,
  STATUS_LABEL_KEY,
  UNIT_LABEL_KEY,
} from '../constants';
import {
  useAddProduceImage,
  useDeleteProduce,
  useProduceDetail,
  useBuyerOffer,
  useDecideBuyerOffer,
} from '../hooks/useProduce';
import type { ProduceOfferDetail } from '../types';
import { formatQuantity, formatRupees, harvestCountdown } from '../utils/format';

export function ProduceDetailScreen({ offerId }: { offerId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();

  const { data: offer, isLoading, isError, refetch } = useProduceDetail(offerId);
  const addImage = useAddProduceImage(offerId);
  const del = useDeleteProduce();
  const buyerOffer = useBuyerOffer(offerId);
  const decideOffer = useDecideBuyerOffer(offerId);

  if (isLoading) {
    return (
      <AgScreen scroll>
        <AgSkeleton className="h-8 w-40 rounded-md" />
        <AgSkeleton className="mt-4 h-48 w-full rounded-card" />
        <AgSkeleton className="mt-4 h-40 w-full rounded-card" />
      </AgScreen>
    );
  }

  if (isError || !offer) {
    return (
      <AgScreen>
        <ProduceBackHeader title={t('produce.detailTitle')} />
        <AgErrorState onRetry={() => void refetch()} />
      </AgScreen>
    );
  }

  const unit = t(UNIT_LABEL_KEY[offer.unit], { defaultValue: offer.unit });
  const countdown = offer.insight ? harvestCountdown(offer.insight.daysToHarvest) : null;
  const countdownLabel = countdown
    ? countdown.key === 'inDays'
      ? t('produce.harvestInDays', { count: countdown.days })
      : countdown.key === 'overdue'
        ? t('produce.harvestOverdue', { count: countdown.days })
        : t(`produce.harvest_${countdown.key}`)
    : null;

  const uploadPhoto = async (pick: () => Promise<string | null>) => {
    const uri = await pick();
    if (!uri) return;
    try {
      const url = await uploadService.uploadImage(uri, 'produce');
      await addImage.mutateAsync({ imageUrl: url, mimeType: 'image/jpeg' });
    } catch {
      Alert.alert(t('produce.uploadFailed'));
    }
  };

  // Offers both camera and gallery -- previously only the gallery was
  // reachable here (2026-08 pre-release audit).
  const onAddPhoto = () => {
    Alert.alert(t('produce.addPhoto'), undefined, [
      { text: t('produce.takePhoto'), onPress: () => void uploadPhoto(capturePhoto) },
      { text: t('produce.chooseGallery'), onPress: () => void uploadPhoto(pickPhoto) },
      { text: t('common.cancel'), style: 'cancel' },
    ]);
  };

  const confirmDelete = () => {
    Alert.alert(t('produce.deleteConfirmTitle'), t('produce.deleteConfirmMessage'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: () => del.mutate(offer.id, { onSuccess: () => router.back() }),
      },
    ]);
  };

  return (
    <AgScreen scroll>
      <ProduceBackHeader
        title={t('produce.detailTitle')}
        right={
          <View className="flex-row items-center">
            <AgPressable
              onPress={() => router.push(`/produce/${offer.id}/edit`)}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={t('produce.edit')}
              className="h-10 w-10 items-center justify-center"
            >
              <Pencil size={20} color={colors.text} />
            </AgPressable>
            <AgPressable
              onPress={confirmDelete}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={t('produce.delete')}
              className="h-10 w-10 items-center justify-center"
            >
              <Trash2 size={20} color={colors.danger} />
            </AgPressable>
          </View>
        }
      />

      {/* Photos */}
      <Gallery offer={offer} onAdd={onAddPhoto} adding={addImage.isPending} />

      <View className="mt-4 flex-row flex-wrap items-center gap-2">
        <AgBadge label={offer.listingRef ?? offer.id} tone="info" />
        <ProduceStatusBadge status={offer.status} />
        {offer.insight ? <HarvestWindowBadge window={offer.insight.harvestWindow} /> : null}
        {offer.expectedGrade ? (
          <AgBadge label={t(GRADE_LABEL_KEY[offer.expectedGrade])} tone="neutral" />
        ) : null}
      </View>

      <AgText variant="headingM" weight="bold" className="mt-2">
        {offer.productName || offer.cropName}
      </AgText>
      {offer.variety ? (
        <AgText variant="body" color="muted">
          {offer.variety}
        </AgText>
      ) : null}

      {/* Key facts */}
      <AgCard className="mt-4 gap-2">
        <Row label={t('produce.quantity')} value={formatQuantity(offer.quantity, unit)} />
        {offer.expectedHarvestDate ? <Row
          label={t('produce.expectedHarvest')}
          value={offer.expectedHarvestDate}
          hint={countdownLabel}
        /> : <Row label={t('produce.listingType')} value={t('produce.availableNow')} />}
        {offer.askingPrice != null ? (
          <Row
            label={t('produce.askingPrice')}
            value={`${formatRupees(offer.askingPrice)} / ${unit}`}
          />
        ) : null}
      </AgCard>

      {/* Procurement insight (deterministic engine) */}
      {offer.insight ? (
        <AgCard className="mt-4">
          <View className="mb-2 flex-row items-center gap-2">
            <TrendingUp size={16} color={colors.primary} />
            <AgText variant="label" weight="semibold">
              {t('produce.procurementInsight')}
            </AgText>
          </View>
          {offer.insight.estimatedMarketValue != null ? (
            <Row
              label={t('produce.estimatedValue')}
              value={formatRupees(offer.insight.estimatedMarketValue)}
              strong
            />
          ) : null}
          {offer.insight.estimatedAskingValue != null ? (
            <Row
              label={t('produce.askingValue')}
              value={formatRupees(offer.insight.estimatedAskingValue)}
            />
          ) : null}
          {offer.insight.priceReference ? (
            <View className="mt-2 border-t border-border pt-2">
              <View className="flex-row items-center gap-1">
                <ShieldCheck size={13} color={colors.success} />
                <AgText variant="caption" color="muted">
                  {t('produce.verifiedPrice', {
                    price: formatRupees(offer.insight.priceReference.modalPrice),
                    source: offer.insight.priceReference.source,
                    date: offer.insight.priceReference.priceDate,
                  })}
                </AgText>
              </View>
            </View>
          ) : (
            <AgText variant="caption" color="muted" className="mt-1">
              {t('produce.noVerifiedPrice')}
            </AgText>
          )}
        </AgCard>
      ) : null}

      {/* Location */}
      {offer.district || offer.village ? (
        <AgCard className="mt-4">
          <View className="flex-row items-center gap-2">
            <MapPin size={15} color={colors.textMuted} />
            <AgText variant="body">
              {[offer.village, offer.block, offer.district].filter(Boolean).join(', ')}
            </AgText>
          </View>
        </AgCard>
      ) : null}

      {/* Notes */}
      {offer.notes ? (
        <AgCard className="mt-4">
          <AgText variant="label" weight="semibold" color="muted" className="mb-1">
            {t('produce.notes')}
          </AgText>
          <AgText variant="body">{offer.notes}</AgText>
        </AgCard>
      ) : null}

      {/* Procurement reference (from the provider channel) */}
      {offer.procurementReference ? (
        <View className="mt-4 flex-row items-center gap-1">
          <CalendarClock size={13} color={colors.textMuted} />
          <AgText variant="caption" color="muted">
            {t('produce.procurementRef', {
              channel: offer.procurementChannel ?? '',
              ref: offer.procurementReference,
            })}
          </AgText>
        </View>
      ) : null}

      {/* Status history */}
      {offer.statusHistory.length > 0 ? (
        <AgCard className="mt-4">
          <View className="mb-2 flex-row items-center gap-2">
            <HistoryIcon size={16} color={colors.primary} />
            <AgText variant="label" weight="semibold">
              {t('produce.statusHistory')}
            </AgText>
          </View>
          <View className="gap-2">
            {offer.statusHistory.map((h) => (
              <View key={h.id} className="flex-row items-center justify-between">
                <AgText variant="bodySmall">
                  {t(STATUS_LABEL_KEY[h.newStatus as keyof typeof STATUS_LABEL_KEY] ?? '', {
                    defaultValue: h.newStatus,
                  })}
                </AgText>
                <AgText variant="caption" color="muted">
                  {h.createdAt.slice(0, 10)}
                </AgText>
              </View>
            ))}
          </View>
        </AgCard>
      ) : null}

      {buyerOffer.data ? (
        <BuyerOfferApprovalCard
          offer={buyerOffer.data}
          deciding={decideOffer.isPending}
          onDecision={(decision) => decideOffer.mutate(decision, {
            onError: () => Alert.alert(t('produce.offerDecisionFailed')),
          })}
        />
      ) : null}

      <AgButton
        title={t('produce.edit')}
        onPress={() => router.push(`/produce/${offer.id}/edit`)}
        variant="secondary"
        fullWidth
        leftIcon={<Pencil size={18} color={colors.primary} />}
        className="mt-6"
      />
      {internalTestFlags.internalFeatureTesting ? (
        <AgButton
          title={t('traceability.open')}
          onPress={() => router.push(`/produce/${offer.id}/traceability`)}
          variant="secondary"
          leftIcon={<Route size={18} color={colors.primary} />}
          className="mt-3"
        />
      ) : null}

      {/* Not-a-marketplace note (docs: no direct transactions) */}
      <AgText variant="caption" color="muted" className="mt-4 text-center">
        {t('produce.procurementNote')}
      </AgText>
    </AgScreen>
  );
}

function Gallery({
  offer,
  onAdd,
  adding,
}: {
  offer: ProduceOfferDetail;
  onAdd: () => void;
  adding: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerClassName="gap-2 py-1"
      className="mt-3"
    >
      {offer.images.map((img) => (
        <Image
          key={img.id}
          source={{ uri: img.imageUrl }}
          style={{ width: 140, height: 140, borderRadius: 16 }}
          contentFit="cover"
        />
      ))}
      {offer.images.length === 0 ? (
        <View className="h-[140px] w-[140px] items-center justify-center rounded-2xl bg-primary/10">
          <Sprout size={32} color={colors.primary} />
        </View>
      ) : null}
      <AgPressable
        onPress={onAdd}
        disabled={adding}
        accessibilityRole="button"
        accessibilityLabel={t('produce.addPhoto')}
        className="h-[140px] w-[140px] items-center justify-center rounded-2xl border border-dashed border-border bg-surface-card"
      >
        <Camera size={26} color={colors.primary} />
        <AgText variant="caption" color="muted" className="mt-1">
          {t('produce.addPhoto')}
        </AgText>
      </AgPressable>
    </ScrollView>
  );
}

function Row({
  label,
  value,
  hint,
  strong,
}: {
  label: string;
  value: string;
  hint?: string | null;
  strong?: boolean;
}) {
  const { colors } = useAppTheme();
  return (
    <View className="flex-row items-center justify-between gap-3">
      <AgText variant="bodySmall" color="muted">
        {label}
      </AgText>
      <View className="items-end">
        <AgText
          variant="body"
          weight={strong ? 'bold' : 'semibold'}
          style={strong ? { color: colors.primary } : undefined}
        >
          {value}
        </AgText>
        {hint ? (
          <AgText variant="caption" color="muted">
            {hint}
          </AgText>
        ) : null}
      </View>
    </View>
  );
}
