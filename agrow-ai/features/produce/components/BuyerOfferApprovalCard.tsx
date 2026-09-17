import { Alert, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgButton, AgCard, AgText } from '@/components/ui';

import type { FrozenBuyerOffer } from '../types';

export function BuyerOfferApprovalCard({
  offer,
  deciding,
  onDecision,
}: {
  offer: FrozenBuyerOffer;
  deciding: boolean;
  onDecision: (decision: 'accepted' | 'rejected') => void;
}) {
  const { t } = useTranslation();
  const terms = offer.terms;
  const gross = Number(terms.quantity) * Number(terms.unit_price);
  const commission = gross * Number(terms.commission_rate || 0) / 100;
  return (
    <AgCard className="mt-4 gap-3">
      <AgText variant="headingS" weight="bold">{t('produce.buyerOfferTitle')}</AgText>
      <AgText variant="body">{terms.buyer_name}</AgText>
      <View className="gap-1">
        <AgText>{t('produce.offerQuantity')}: {terms.quantity} {terms.price_unit}</AgText>
        <AgText>{t('produce.offerPrice')}: ₹{terms.unit_price} / {terms.price_unit}</AgText>
        <AgText>{t('produce.transportCost')}: ₹{terms.transport_cost}</AgText>
        <AgText>{t('produce.commission')}: {terms.commission_rate}% (₹{commission.toFixed(2)})</AgText>
        <AgText weight="bold">{t('produce.estimatedFarmerAmount')}: ₹{Math.max(0, gross - Number(terms.transport_cost) - commission).toFixed(2)}</AgText>
      </View>
      {offer.decision ? (
        <AgText weight="semibold">{t(`produce.offerDecision.${offer.decision}`)}</AgText>
      ) : (
        <View className="flex-row gap-2">
          <View className="flex-1"><AgButton title={t('produce.rejectOffer')} variant="secondary" disabled={deciding} onPress={() => Alert.alert(t('produce.rejectOffer'), t('produce.rejectOfferConfirm'), [{ text: t('common.cancel') }, { text: t('produce.rejectOffer'), style: 'destructive', onPress: () => onDecision('rejected') }])} /></View>
          <View className="flex-1"><AgButton title={t('produce.acceptOffer')} loading={deciding} onPress={() => Alert.alert(t('produce.acceptOffer'), t('produce.acceptOfferConfirm'), [{ text: t('common.cancel') }, { text: t('produce.acceptOffer'), onPress: () => onDecision('accepted') }])} /></View>
        </View>
      )}
      <AgText variant="caption" color="muted">{t('produce.frozenOfferNotice')}</AgText>
    </AgCard>
  );
}
