import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { ArrowLeft, CalendarDays, CheckCircle2, ChevronRight, ClipboardList, Clock, Hourglass, Leaf, MapPin, PackagePlus, ShieldCheck, ShoppingBasket, XCircle } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, TouchableOpacity, View } from 'react-native';

import { AgButton, AgCard, AgDropdown, AgInput, AgScreen, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { sellApi, type SellBatch } from './sellApi';

const REVIEW_STATES = new Set(['submitted', 'under_review', 'clarification_required', 'inspection_scheduled', 'inspection_completed']);
const UNITS = ['kg', 'litre', 'bag', 'packet'];
const PRODUCT_DESCRIPTIONS: Record<string, string> = {
  vermicompost: 'Nutrient-rich compost made by earthworms, ideal for healthier soil and better crop yield.',
  panchagavya: 'Traditional organic liquid made from cow products that supports plant growth and immunity.',
  azolla: 'Fast-growing aquatic fern, rich in nitrogen and useful as organic fertilizer or animal feed.',
  trichoderma: 'Beneficial fungus that supports root health and helps control soil-borne diseases.',
  neem: 'Organic manure that supports soil health and helps manage pests naturally.',
};
const productDescription = (name: string) => Object.entries(PRODUCT_DESCRIPTIONS).find(([key]) => name.toLowerCase().includes(key))?.[1] ?? 'Organic input submitted for quality checking before a purchase offer.';

/** Farmer sells organic inputs to Agrownex: apply once, then offer batches; we check quality, buy and resell. */
export function SellToAgrownexScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors, isDark } = useAppTheme();
  const profile = useQuery({ queryKey: ['sell', 'profile'], queryFn: sellApi.getProfile });
  const status = profile.data?.status;

  return (
    <AgScreen scroll keyboardAvoiding backgroundColor={isDark ? '#131B15' : '#F7FAF4'} contentContainerStyle={styles.screen}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} style={[styles.back, { backgroundColor: isDark ? '#1D3926' : '#EAF5E7' }]}>
          <ArrowLeft size={23} color={isDark ? colors.text : '#0B4A31'} />
        </TouchableOpacity>
        <View style={[styles.marketMark, { backgroundColor: isDark ? '#1D3926' : '#EEF8EB' }]}><ShoppingBasket size={18} color={colors.primary} /><AgText variant="caption" weight="bold" style={{ color: colors.primary }}>MARKET</AgText></View>
      </View>
      {status && REVIEW_STATES.has(status) ? <ReviewExperience status={status} profile={profile.data} /> : status === 'approved' ? <ApprovedHero /> : <><View style={styles.heroCopy}><AgText variant="headingL" weight="bold" style={[styles.title, { color: isDark ? colors.text : '#073F2A' }]}>{t('inputsSell.title')}</AgText><AgText variant="body" style={[styles.intro, { color: colors.textMuted }]}>{t('inputsSell.intro')}</AgText></View><View style={[styles.processCard, { backgroundColor: isDark ? '#1D3424' : '#EAF6E6', borderColor: isDark ? '#31573B' : '#D1E8CB' }]}><View style={[styles.processIcon, { backgroundColor: isDark ? '#25462D' : '#D8EFD2' }]}><ShieldCheck size={24} color={colors.primary} /></View><View style={styles.processCopy}><AgText weight="bold" style={{ color: colors.text }}>Quality checked before resale</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>Apply once. We review your inputs and may arrange a farm visit.</AgText></View></View></>}

      {profile.isLoading ? <AgText style={{ marginTop: 16 }}>{t('common.loading')}</AgText> : null}
      {profile.isError ? <AgButton className="mt-4" title={t('common.retry')} onPress={() => void profile.refetch()} /> : null}

      {profile.isSuccess && (!profile.data || status === 'draft') ? <ApplyForm /> : null}
      {status === 'rejected' || status === 'suspended' || status === 'expired' ? (
        <StatusCard icon="no" title={t('inputsSell.applicationClosed')} body={t('inputsSell.applicationClosedBody')} />
      ) : null}
      {status === 'approved' ? <ApprovedSeller /> : null}
    </AgScreen>
  );
}

function ReviewExperience({ status, profile }: { status: string; profile: { contact_name: string | null; village: string | null; district: string | null } | null | undefined }) {
  const { t } = useTranslation(); const { colors, isDark } = useAppTheme();
  const currentStep = status === 'submitted' ? 0 : status === 'inspection_scheduled' || status === 'inspection_completed' ? 2 : 1;
  const details = [profile?.contact_name, profile?.village, profile?.district].filter(Boolean).join(' · ');
  const stages = [{ label: 'Submitted', body: 'Application received', icon: CheckCircle2 }, { label: 'Under review', body: 'Our team is checking', icon: Clock }, { label: 'Quality check', body: 'May visit your farm', icon: ClipboardList }];
  return <><View style={styles.reviewHero}><Image source={require('@/assets/images/auth-hero.png')} contentFit="cover" contentPosition="right bottom" style={styles.reviewHeroImage} accessible={false} /><View style={[styles.reviewHeroWash, { backgroundColor: isDark ? 'rgba(19,27,21,0.60)' : 'rgba(247,250,244,0.52)' }]} /><View style={styles.reviewHeroCopy}><View style={[styles.sellerBadge, { backgroundColor: isDark ? '#1D3926' : '#EAF6E6' }]}><Leaf size={16} color={colors.primary} /><AgText variant="caption" weight="bold" style={{ color: colors.primary }}>ORGANIC SELLER</AgText></View><AgText variant="headingL" weight="bold" style={[styles.reviewTitle, { color: isDark ? colors.text : '#073F2A' }]}>{t('inputsSell.title')}</AgText><AgText variant="body" style={[styles.reviewIntro, { color: colors.textMuted }]}>{t('inputsSell.intro')}</AgText></View></View><View style={[styles.reviewCard, { backgroundColor: isDark ? '#202A21' : '#FFFDFC', borderColor: isDark ? '#35463A' : '#E2ECE0' }]}><View style={styles.reviewHeading}><View style={[styles.reviewStatusIcon, { backgroundColor: '#FFF0D3' }]}><Clock size={31} color="#E99911" /></View><View style={styles.reviewHeadingCopy}><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>{t('inputsSell.applicationReview')}</AgText><AgText variant="bodySmall" style={{ color: colors.textMuted }}>{t('inputsSell.applicationReviewBody')}</AgText></View></View><View style={styles.timeline}>{stages.map((stage, index) => { const Icon = stage.icon; const active = index <= currentStep; const current = index === currentStep; return <View key={stage.label} style={styles.stage}><View style={styles.stageVisual}><View style={[styles.stageIcon, { backgroundColor: active ? (current ? '#FFF0D3' : '#E3F4DE') : (isDark ? '#27302A' : '#F3F5F2'), borderColor: active ? (current ? '#E99911' : colors.primary) : (isDark ? '#4A554C' : '#CDD4CE') }]}><Icon size={24} color={active ? (current ? '#E99911' : colors.primary) : colors.textMuted} /></View>{index < stages.length - 1 ? <View style={[styles.stageLine, { backgroundColor: index < currentStep ? colors.primary : (isDark ? '#3A433C' : '#E0E5E0') }]} /> : null}</View><AgText variant="bodySmall" weight="bold" style={[styles.stageLabel, { color: active ? colors.text : colors.textMuted }]}>{stage.label}</AgText><AgText variant="caption" style={[styles.stageBody, { color: colors.textMuted }]}>{stage.body}</AgText></View>; })}</View><View style={[styles.reviewEstimate, { backgroundColor: isDark ? '#193021' : '#F0F8EC' }]}><View style={[styles.estimateIcon, { backgroundColor: isDark ? '#25462D' : '#DDF0DA' }]}><Clock size={21} color={colors.primary} /></View><View style={{ flex: 1 }}><AgText variant="bodySmall" weight="bold" style={{ color: colors.text }}>Typical review time: 2–5 days</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>We will contact you soon.</AgText></View></View><TouchableOpacity accessibilityRole="button" onPress={() => Alert.alert(t('inputsSell.title'), details || t('inputsSell.applicationReviewBody'))} activeOpacity={0.78} style={[styles.detailsButton, { borderColor: isDark ? '#3A5140' : '#D5E4D3' }]}><View style={[styles.detailsIcon, { backgroundColor: isDark ? '#25462D' : '#EAF6E6' }]}><ClipboardList size={21} color={colors.primary} /></View><AgText variant="body" weight="semibold" style={{ flex: 1, color: colors.text }}>View application details</AgText><ArrowLeft size={22} color={colors.primary} style={{ transform: [{ rotate: '180deg' }] }} /></TouchableOpacity></View></>;
}

function ApprovedHero() {
  const { t } = useTranslation(); const { colors, isDark } = useAppTheme();
  return <><View style={styles.approvedHero}><Image source={require('@/assets/images/auth-hero.png')} contentFit="cover" contentPosition="right bottom" style={styles.approvedHeroImage} accessible={false} /><View style={[styles.reviewHeroWash, { backgroundColor: isDark ? 'rgba(19,27,21,0.56)' : 'rgba(247,250,244,0.46)' }]} /><View style={styles.approvedHeroCopy}><View style={[styles.sellerBadge, { backgroundColor: isDark ? '#1D3926' : '#EAF6E6' }]}><Leaf size={16} color={colors.primary} /><AgText variant="caption" weight="bold" style={{ color: colors.primary }}>ORGANIC SELLER</AgText></View><AgText variant="headingL" weight="bold" style={[styles.approvedTitle, { color: isDark ? colors.text : '#073F2A' }]}>Sell to <AgText variant="headingL" weight="bold" style={{ color: colors.primary }}>AgrowNex</AgText></AgText><AgText variant="body" style={[styles.reviewIntro, { color: colors.textMuted }]}>{t('inputsSell.intro')}</AgText></View></View><View style={[styles.approvedBanner, { backgroundColor: isDark ? '#1D3424' : '#EAF6E6', borderColor: isDark ? '#31573B' : '#D1E8CB' }]}><View style={[styles.approvedIcon, { backgroundColor: colors.primary }]}><CheckCircle2 size={26} color="#FFFFFF" /></View><View style={{ flex: 1 }}><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>You are an approved seller</AgText><AgText variant="bodySmall" style={{ color: colors.textMuted }}>Offer a batch whenever you have product ready.</AgText></View></View></>;
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
  const { colors, isDark } = useAppTheme();
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
  const fieldBackground = isDark ? '#202A21' : '#FFFFFF'; const fieldBorder = isDark ? '#3A5140' : '#DCE8DA';
  return <View style={[styles.application, { backgroundColor: isDark ? '#202A21' : '#FFFDFC', borderColor: isDark ? '#35463A' : '#E2ECE0' }]}><View style={styles.applicationTop}><View style={[styles.applicationIcon, { backgroundColor: isDark ? '#25462D' : '#DDF0DA' }]}><Leaf size={22} color={colors.primary} /></View><View style={styles.applicationCopy}><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>{t('inputsSell.applyTitle')}</AgText><AgText variant="bodySmall" style={{ color: colors.textMuted }}>{t('inputsSell.applyBody')}</AgText></View></View><View style={[styles.formDivider, { backgroundColor: isDark ? '#35463A' : '#E2ECE0' }]} /><AgInput light={!isDark} fieldBackgroundColor={fieldBackground} fieldBorderColor={fieldBorder} label={t('inputsSell.name')} value={name} onChangeText={setName} required /><AgInput light={!isDark} fieldBackgroundColor={fieldBackground} fieldBorderColor={fieldBorder} containerClassName="mt-3" label={t('inputsSell.phone')} value={phone} onChangeText={setPhone} keyboardType="phone-pad" required /><View style={styles.fieldRow}><View style={styles.fieldHalf}><AgInput light={!isDark} fieldBackgroundColor={fieldBackground} fieldBorderColor={fieldBorder} containerClassName="mt-3" label={t('inputsSell.village')} value={village} onChangeText={setVillage} /></View><View style={styles.fieldHalf}><AgInput light={!isDark} fieldBackgroundColor={fieldBackground} fieldBorderColor={fieldBorder} containerClassName="mt-3" label={t('inputsSell.district')} value={district} onChangeText={setDistrict} /></View></View><AgInput light={!isDark} fieldBackgroundColor={fieldBackground} fieldBorderColor={fieldBorder} containerClassName="mt-3" label={t('inputsSell.whatYouMake')} value={products} onChangeText={setProducts} multiline placeholder={t('inputsSell.whatYouMakeHint')} /><View style={[styles.locationNote, { backgroundColor: isDark ? '#193021' : '#F0F8EC' }]}><MapPin size={16} color={colors.primary} /><AgText variant="caption" style={{ flex: 1, color: colors.textMuted }}>Your location helps our quality team plan a farm visit.</AgText></View><AgButton className="mt-4" title={t('inputsSell.submitApplication')} onPress={() => apply.mutate()} disabled={!valid} loading={apply.isPending} /></View>;
}

function ApprovedSeller() {
  const { t } = useTranslation();
  const { colors, isDark } = useAppTheme();
  const [showForm, setShowForm] = useState(true);
  const batches = useQuery({ queryKey: ['sell', 'batches'], queryFn: sellApi.myBatches });
  const productTypes = useQuery({ queryKey: ['sell', 'productTypes'], queryFn: sellApi.productTypes });
  return (
    <>
      {showForm ? <OfferBatchForm onDone={() => setShowForm(false)} /> : <AgButton className="mt-4" title={t('inputsSell.offerBatch')} onPress={() => setShowForm(true)} leftIcon={<PackagePlus size={18} color={colors.onPrimary} />} />}
      <View style={[styles.batchHeader, { borderColor: isDark ? '#35463A' : '#E2ECE0' }]}><View style={[styles.applicationIcon, { backgroundColor: isDark ? '#25462D' : '#DDF0DA' }]}><PackagePlus size={21} color={colors.primary} /></View><AgText variant="headingS" weight="bold" style={{ flex: 1, color: colors.text }}>{t('inputsSell.myBatches')}</AgText><View style={[styles.viewAll, { backgroundColor: isDark ? '#24452D' : '#EEF8EB' }]}><AgText variant="caption" weight="semibold" style={{ color: colors.primary }}>View all</AgText><ChevronRight size={16} color={colors.primary} /></View></View>
      {batches.data?.length === 0 ? <View style={[styles.batchEmpty, { backgroundColor: isDark ? '#202A21' : '#FFFDFC', borderColor: isDark ? '#35463A' : '#E2ECE0' }]}><View style={[styles.emptyIcon, { backgroundColor: isDark ? '#25462D' : '#EAF6E6' }]}><PackagePlus size={27} color={colors.primary} /></View><View style={{ flex: 1 }}><AgText weight="bold" style={{ color: colors.text }}>{t('inputsSell.noBatches')}</AgText><AgText variant="caption" style={{ color: colors.textMuted }}>Submit your first batch to get started.</AgText></View></View> : null}
      {batches.data?.map((batch) => <BatchCard key={batch.id} batch={batch} productName={productTypes.data?.find((type) => type.id === batch.product_type_id)?.name ?? batch.batch_code} />)}
    </>
  );
}

function OfferBatchForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const { colors, isDark } = useAppTheme();
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
    <View style={[styles.batchForm, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <View style={styles.applicationTop}><View style={[styles.applicationIcon, { backgroundColor: isDark ? '#25462D' : '#EAF6E6' }]}><Leaf size={22} color={colors.primary} /></View><View style={styles.applicationCopy}><AgText variant="headingS" weight="bold" style={{ color: colors.text }}>{t('inputsSell.offerBatch')}</AgText><AgText variant="bodySmall" style={{ color: colors.textMuted }}>Tell us about your product and quantity. We will check quality and send you a purchase offer.</AgText></View></View>
      {types.data?.length === 0 ? <AgText variant="bodySmall" style={{ marginTop: 14, color: colors.textMuted }}>{t('inputsSell.noProductTypes')}</AgText> : null}
      <AgDropdown
        light={!isDark} optionVariant="organicProduct" title="Choose a product" label={t('inputsSell.product')} placeholder={t('inputsSell.chooseProduct')} value={typeId} onChange={setTypeId}
        options={(types.data ?? []).map((type) => { const label = language === 'ta' && type.name_ta ? type.name_ta : type.name; return { value: type.id, label, description: productDescription(type.name) }; })}
      />
      <AgInput containerClassName="mt-3" label={t('inputsSell.quantity')} value={quantity} onChangeText={setQuantity} keyboardType="decimal-pad" required />
      <AgDropdown label={t('inputsSell.unit')} placeholder={t('inputsSell.unit')} value={unit} onChange={setUnit} options={UNITS.map((u) => ({ value: u, label: t(`inputsSell.units.${u}`) }))} />
      <AgInput containerClassName="mt-3" label={t('inputsSell.expectedPrice', { unit: t(`inputsSell.units.${unit}`) })} value={price} onChangeText={setPrice} keyboardType="decimal-pad" />
      <View style={[styles.locationNote, { backgroundColor: isDark ? '#193021' : '#F0F8EC' }]}><ShieldCheck size={17} color={colors.primary} /><AgText variant="caption" style={{ flex: 1, color: colors.textMuted }}>{t('inputsSell.qualityNote')}</AgText></View>
      <View style={styles.batchFormActions}>
        <AgButton fullWidth={false} className="flex-1" title={t('common.cancel')} variant="outline" onPress={onDone} />
        <AgButton fullWidth={false} className="flex-1" title={t('inputsSell.sendBatch')} onPress={() => create.mutate()} disabled={!valid} loading={create.isPending} />
      </View>
    </View>
  );
}

function BatchCard({ batch, productName }: { batch: SellBatch; productName: string }) {
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
  const reviewState = batch.status === 'under_review' || batch.status === 'submitted';
  const date = new Date(batch.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  return (
    <View style={[styles.batchCard, { backgroundColor: colors.card, borderColor: colors.border }]}><View style={styles.batchRow}><View style={[styles.batchArt, { backgroundColor: '#EAF6E6' }]}><Leaf size={34} color={colors.primary} /></View><View style={styles.batchRowCopy}><AgText weight="bold" numberOfLines={1} style={{ color: colors.text }}>{productName}</AgText><AgText variant="bodySmall" style={{ color: colors.textMuted }}>{Number(batch.batch_quantity)} {t(`inputsSell.units.${batch.unit}`, { defaultValue: batch.unit })}{batch.expected_procurement_price ? `  |  ₹${Number(batch.expected_procurement_price)}/${batch.unit}` : ''}</AgText><View style={styles.batchDate}><CalendarDays size={14} color={colors.textMuted} /><AgText variant="caption" style={{ color: colors.textMuted }}>{date}</AgText></View></View><View style={[styles.batchStatus, { backgroundColor: reviewState ? '#FFF1D9' : '#E5F0FF' }]}>{reviewState ? <Clock size={16} color="#D97307" /> : <Hourglass size={16} color="#2473C9" />}<AgText variant="caption" weight="semibold" style={{ color: reviewState ? '#B65F00' : '#1D68B8' }}>{reviewState ? 'Under review' : statusLabel}</AgText></View></View>
      {offered && offer.data ? (
        <View style={{ marginTop: 10 }}>
          <AgText weight="bold" style={{ color: colors.text }}>
            {t('inputsSell.offerText', { qty: Number(offer.data.offered_quantity), unit: offer.data.unit, price: Number(offer.data.offered_unit_price) })}
          </AgText>
          <View style={[styles.row, { marginTop: 8 }]}>
            <AgButton fullWidth={false} className="flex-1" title={t('inputsSell.decline')} variant="outline" onPress={() => decide.mutate(false)} disabled={decide.isPending} />
            <AgButton fullWidth={false} className="flex-1" title={t('inputsSell.accept')} onPress={() => decide.mutate(true)} loading={decide.isPending} />
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { paddingTop: 8, paddingBottom: 40 },
  header: { minHeight: 52, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  back: { width: 46, height: 46, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  marketMark: { minHeight: 34, paddingHorizontal: 11, borderRadius: 17, flexDirection: 'row', alignItems: 'center', gap: 6 },
  heroCopy: { paddingTop: 23, paddingBottom: 18 },
  title: { letterSpacing: -0.8 },
  intro: { marginTop: 8, lineHeight: 24, maxWidth: 390 },
  processCard: { minHeight: 84, padding: 14, borderRadius: 18, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 12 },
  processIcon: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  processCopy: { flex: 1, gap: 3 },
  reviewHero: { height: 286, marginTop: 12, borderRadius: 24, overflow: 'hidden' },
  reviewHeroImage: { position: 'absolute', right: 0, bottom: 0, width: '100%', height: '100%' },
  reviewHeroWash: { position: 'absolute', inset: 0 },
  reviewHeroCopy: { padding: 20, maxWidth: '76%' },
  sellerBadge: { alignSelf: 'flex-start', minHeight: 30, paddingHorizontal: 10, borderRadius: 15, flexDirection: 'row', alignItems: 'center', gap: 6 },
  reviewTitle: { marginTop: 13, letterSpacing: -0.8 },
  reviewIntro: { marginTop: 8, lineHeight: 23 },
  reviewCard: { marginTop: -28, padding: 18, borderRadius: 24, borderWidth: 1, shadowColor: '#24482D', shadowOpacity: 0.12, shadowRadius: 18, shadowOffset: { width: 0, height: 7 }, elevation: 3 },
  reviewHeading: { flexDirection: 'row', alignItems: 'center', gap: 13 },
  reviewStatusIcon: { width: 58, height: 58, borderRadius: 29, alignItems: 'center', justifyContent: 'center' },
  reviewHeadingCopy: { flex: 1, gap: 4 },
  timeline: { marginTop: 24, flexDirection: 'row' },
  stage: { flex: 1, alignItems: 'center', minWidth: 0 },
  stageVisual: { width: '100%', height: 48, flexDirection: 'row', alignItems: 'center' },
  stageIcon: { width: 48, height: 48, borderRadius: 24, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  stageLine: { flex: 1, height: 3 },
  stageLabel: { marginTop: 10, textAlign: 'center', lineHeight: 18 },
  stageBody: { marginTop: 3, paddingHorizontal: 3, textAlign: 'center', lineHeight: 16 },
  reviewEstimate: { minHeight: 72, marginTop: 24, padding: 12, borderRadius: 16, flexDirection: 'row', alignItems: 'center', gap: 10 },
  estimateIcon: { width: 42, height: 42, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
  detailsButton: { minHeight: 60, marginTop: 18, paddingHorizontal: 12, borderRadius: 16, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  detailsIcon: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  approvedHero: { height: 292, marginTop: 12, borderRadius: 24, overflow: 'hidden' },
  approvedHeroImage: { position: 'absolute', right: 0, bottom: 0, width: '100%', height: '100%' },
  approvedHeroCopy: { padding: 20, maxWidth: '76%' },
  approvedTitle: { marginTop: 13, letterSpacing: -0.8 },
  approvedBanner: { minHeight: 96, marginTop: -26, padding: 16, borderRadius: 20, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 13 },
  approvedIcon: { width: 54, height: 54, borderRadius: 27, alignItems: 'center', justifyContent: 'center' },
  batchForm: { marginTop: 18, padding: 17, borderRadius: 22, borderWidth: 1 },
  batchFormActions: { marginTop: 14, flexDirection: 'row', gap: 10 },
  batchHeader: { marginTop: 20, paddingTop: 18, borderTopWidth: StyleSheet.hairlineWidth, flexDirection: 'row', alignItems: 'center', gap: 10 },
  viewAll: { minHeight: 32, paddingHorizontal: 10, borderRadius: 16, flexDirection: 'row', alignItems: 'center', gap: 2 },
  batchEmpty: { minHeight: 92, marginTop: 12, padding: 15, borderRadius: 18, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 12 },
  emptyIcon: { width: 50, height: 50, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  batchCard: { marginTop: 10, padding: 11, borderRadius: 18, borderWidth: 1 },
  batchRow: { minHeight: 74, flexDirection: 'row', alignItems: 'center', gap: 10 },
  batchArt: { width: 62, height: 70, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  batchRowCopy: { flex: 1, minWidth: 0, gap: 3 },
  batchDate: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  batchStatus: { maxWidth: 138, minHeight: 30, paddingHorizontal: 8, borderRadius: 15, flexDirection: 'row', alignItems: 'center', gap: 5 },
  application: { marginTop: 16, padding: 16, borderRadius: 22, borderWidth: 1 },
  applicationTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 11 },
  applicationIcon: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  applicationCopy: { flex: 1, gap: 3 },
  formDivider: { height: StyleSheet.hairlineWidth, marginVertical: 15 },
  fieldRow: { flexDirection: 'row', gap: 10 },
  fieldHalf: { flex: 1, minWidth: 0 },
  locationNote: { marginTop: 12, padding: 11, borderRadius: 12, flexDirection: 'row', alignItems: 'center', gap: 7 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
});
