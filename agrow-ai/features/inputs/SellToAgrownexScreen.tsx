import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { ArrowLeft, CheckCircle2, Clock, PackagePlus, XCircle } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, TouchableOpacity, View } from 'react-native';

import { AgButton, AgCard, AgDropdown, AgInput, AgScreen, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { sellApi, type SellBatch } from './sellApi';

const REVIEW_STATES = new Set(['submitted', 'under_review', 'clarification_required', 'inspection_scheduled', 'inspection_completed']);
const UNITS = ['kg', 'litre', 'bag', 'packet'];

/** Farmer sells organic inputs to Agrownex: apply once, then offer batches; we check quality, buy and resell. */
export function SellToAgrownexScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const profile = useQuery({ queryKey: ['sell', 'profile'], queryFn: sellApi.getProfile });
  const status = profile.data?.status;

  return (
    <AgScreen scroll>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} style={styles.back}>
          <ArrowLeft size={24} color={colors.text} />
        </TouchableOpacity>
        <AgText variant="headingM" weight="bold" style={{ flex: 1, color: colors.text }}>{t('inputsSell.title')}</AgText>
      </View>
      <AgText variant="body" style={{ color: colors.textMuted, marginTop: 6 }}>{t('inputsSell.intro')}</AgText>

      {profile.isLoading ? <AgText style={{ marginTop: 16 }}>{t('common.loading')}</AgText> : null}
      {profile.isError ? <AgButton className="mt-4" title={t('common.retry')} onPress={() => void profile.refetch()} /> : null}

      {profile.isSuccess && (!profile.data || status === 'draft') ? <ApplyForm /> : null}
      {status && REVIEW_STATES.has(status) ? (
        <StatusCard icon="wait" title={t('inputsSell.applicationReview')} body={t('inputsSell.applicationReviewBody')} />
      ) : null}
      {status === 'rejected' || status === 'suspended' || status === 'expired' ? (
        <StatusCard icon="no" title={t('inputsSell.applicationClosed')} body={t('inputsSell.applicationClosedBody')} />
      ) : null}
      {status === 'approved' ? <ApprovedSeller /> : null}
    </AgScreen>
  );
}

function StatusCard({ icon, title, body }: { icon: 'wait' | 'no' | 'ok'; title: string; body: string }) {
  const { colors } = useAppTheme();
  const Icon = icon === 'wait' ? Clock : icon === 'no' ? XCircle : CheckCircle2;
  const tint = icon === 'no' ? colors.danger : icon === 'wait' ? '#C67909' : colors.primary;
  return (
    <AgCard className="mt-4">
      <View style={styles.row}><Icon size={22} color={tint} /><AgText weight="bold" style={{ flex: 1, color: colors.text }}>{title}</AgText></View>
      <AgText variant="bodySmall" style={{ color: colors.textMuted, marginTop: 6 }}>{body}</AgText>
    </AgCard>
  );
}

function ApplyForm() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [village, setVillage] = useState('');
  const [district, setDistrict] = useState('');
  const [products, setProducts] = useState('');
  const apply = useMutation({
    mutationFn: () => sellApi.applyAndSubmit({
      contact_name: name.trim(), contact_phone: phone.trim(), village: village.trim() || null,
      district: district.trim() || null, production_location: village.trim() || null,
      production_capacity_note: products.trim() || null,
    }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['sell'] }); Alert.alert(t('inputsSell.applied')); },
    onError: () => Alert.alert(t('inputsSell.error')),
  });
  const valid = name.trim().length > 1 && /^\+?\d{10,13}$/.test(phone.trim());
  return (
    <AgCard className="mt-4">
      <AgText variant="headingS" weight="bold">{t('inputsSell.applyTitle')}</AgText>
      <AgText variant="bodySmall" style={{ marginTop: 4 }}>{t('inputsSell.applyBody')}</AgText>
      <AgInput containerClassName="mt-3" label={t('inputsSell.name')} value={name} onChangeText={setName} required />
      <AgInput containerClassName="mt-3" label={t('inputsSell.phone')} value={phone} onChangeText={setPhone} keyboardType="phone-pad" required />
      <AgInput containerClassName="mt-3" label={t('inputsSell.village')} value={village} onChangeText={setVillage} />
      <AgInput containerClassName="mt-3" label={t('inputsSell.district')} value={district} onChangeText={setDistrict} />
      <AgInput containerClassName="mt-3" label={t('inputsSell.whatYouMake')} value={products} onChangeText={setProducts} multiline placeholder={t('inputsSell.whatYouMakeHint')} />
      <AgButton className="mt-4" title={t('inputsSell.submitApplication')} onPress={() => apply.mutate()} disabled={!valid} loading={apply.isPending} />
    </AgCard>
  );
}

function ApprovedSeller() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [showForm, setShowForm] = useState(false);
  const batches = useQuery({ queryKey: ['sell', 'batches'], queryFn: sellApi.myBatches });
  return (
    <>
      <StatusCard icon="ok" title={t('inputsSell.approvedTitle')} body={t('inputsSell.approvedBody')} />
      {showForm ? <OfferBatchForm onDone={() => setShowForm(false)} /> : (
        <AgButton className="mt-4" title={t('inputsSell.offerBatch')} onPress={() => setShowForm(true)} leftIcon={<PackagePlus size={18} color={colors.onPrimary} />} />
      )}
      <AgText variant="headingS" weight="bold" style={{ marginTop: 20, color: colors.text }}>{t('inputsSell.myBatches')}</AgText>
      {batches.data?.length === 0 ? <AgText variant="bodySmall" style={{ color: colors.textMuted, marginTop: 6 }}>{t('inputsSell.noBatches')}</AgText> : null}
      {batches.data?.map((batch) => <BatchCard key={batch.id} batch={batch} />)}
    </>
  );
}

function OfferBatchForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const queryClient = useQueryClient();
  const types = useQuery({ queryKey: ['sell', 'productTypes'], queryFn: sellApi.productTypes });
  const [typeId, setTypeId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('kg');
  const [price, setPrice] = useState('');
  const create = useMutation({
    mutationFn: () => sellApi.createAndSubmitBatch({
      product_type_id: typeId, batch_quantity: quantity.trim(), unit,
      expected_procurement_price: price.trim() || null,
    }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['sell', 'batches'] }); Alert.alert(t('inputsSell.batchSent')); onDone(); },
    onError: () => Alert.alert(t('inputsSell.error')),
  });
  const valid = Boolean(typeId) && Number(quantity) > 0 && (!price.trim() || Number(price) > 0);
  return (
    <AgCard className="mt-4">
      <AgText variant="headingS" weight="bold">{t('inputsSell.offerBatch')}</AgText>
      {types.data?.length === 0 ? <AgText variant="bodySmall" style={{ marginTop: 6 }}>{t('inputsSell.noProductTypes')}</AgText> : null}
      <AgDropdown
        label={t('inputsSell.product')} placeholder={t('inputsSell.chooseProduct')} value={typeId} onChange={setTypeId}
        options={(types.data ?? []).map((type) => ({ value: type.id, label: language === 'ta' && type.name_ta ? type.name_ta : type.name }))}
      />
      <AgInput containerClassName="mt-3" label={t('inputsSell.quantity')} value={quantity} onChangeText={setQuantity} keyboardType="decimal-pad" required />
      <AgDropdown label={t('inputsSell.unit')} placeholder={t('inputsSell.unit')} value={unit} onChange={setUnit} options={UNITS.map((u) => ({ value: u, label: t(`inputsSell.units.${u}`) }))} />
      <AgInput containerClassName="mt-3" label={t('inputsSell.expectedPrice', { unit: t(`inputsSell.units.${unit}`) })} value={price} onChangeText={setPrice} keyboardType="decimal-pad" />
      <AgText variant="caption" style={{ marginTop: 6 }}>{t('inputsSell.qualityNote')}</AgText>
      <View style={[styles.row, { marginTop: 12 }]}>
        <AgButton title={t('common.cancel')} variant="secondary" onPress={onDone} className="flex-1" />
        <AgButton title={t('inputsSell.sendBatch')} onPress={() => create.mutate()} disabled={!valid} loading={create.isPending} className="flex-1" />
      </View>
    </AgCard>
  );
}

function BatchCard({ batch }: { batch: SellBatch }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const queryClient = useQueryClient();
  const offered = batch.status === 'procurement_offered';
  const offer = useQuery({ queryKey: ['sell', 'offer', batch.id], queryFn: () => sellApi.offer(batch.id), enabled: offered });
  const decide = useMutation({
    mutationFn: (accept: boolean) => sellApi.decideOffer(batch.id, accept),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['sell'] }),
    onError: () => Alert.alert(t('inputsSell.error')),
  });
  const statusLabel = t(`inputsSell.batchStatus.${batch.status}`, { defaultValue: batch.status.replaceAll('_', ' ') });
  return (
    <AgCard className="mt-3">
      <View style={styles.row}>
        <AgText weight="bold" style={{ flex: 1, color: colors.text }}>{batch.batch_code}</AgText>
        <AgText variant="caption" weight="bold" style={{ color: colors.primary }}>{statusLabel}</AgText>
      </View>
      <AgText variant="bodySmall" style={{ color: colors.textMuted, marginTop: 4 }}>
        {Number(batch.batch_quantity)} {t(`inputsSell.units.${batch.unit}`, { defaultValue: batch.unit })}
        {batch.expected_procurement_price ? ` · ₹${Number(batch.expected_procurement_price)}` : ''}
      </AgText>
      {batch.latest_review_note ? <AgText variant="caption" style={{ marginTop: 4 }}>{batch.latest_review_note}</AgText> : null}
      {offered && offer.data ? (
        <View style={{ marginTop: 10 }}>
          <AgText weight="bold" style={{ color: colors.text }}>
            {t('inputsSell.offerText', { qty: Number(offer.data.offered_quantity), unit: offer.data.unit, price: Number(offer.data.offered_unit_price) })}
          </AgText>
          <View style={[styles.row, { marginTop: 8 }]}>
            <AgButton title={t('inputsSell.decline')} variant="secondary" onPress={() => decide.mutate(false)} disabled={decide.isPending} className="flex-1" />
            <AgButton title={t('inputsSell.accept')} onPress={() => decide.mutate(true)} loading={decide.isPending} className="flex-1" />
          </View>
        </View>
      ) : null}
    </AgCard>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
});
