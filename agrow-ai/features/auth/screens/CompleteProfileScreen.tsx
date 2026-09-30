import { zodResolver } from '@hookform/resolvers/zod';
import { Image } from 'expo-image';
import { StatusBar } from 'expo-status-bar';
import { ArrowLeft, ArrowRight, Building2, CalendarDays, Check, ChevronDown, GraduationCap, Landmark, LocateFixed, Map as MapIcon, MapPinned, PackageOpen, Phone, Sprout, Trash2, UserRound, Warehouse } from 'lucide-react-native';
import { useMemo, useState, type ReactNode } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, Alert, Modal, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AgDistrictDropdown, AgInput, AgPressable, AgScreen, AgSpinner, AgText } from '@/components/ui';
import { useLanguage } from '@/hooks/useLanguage';
import { useJoinPartnerOrganization, useMyPartnerLinks, usePartnerDirectory, type PartnerLinkRequest } from '@/features/partnerLinks';
import { TAMIL_NADU_DISTRICTS } from '@/constants/locations';

import { ProductMultiSelect } from '../components/ProductMultiSelect';
import { productLabel, toFormUnit, type OnboardingProductOption } from '../components/onboardingData';
import { useAuth } from '../hooks/useAuth';
import { useCompleteProfile } from '../hooks/useAuthActions';
import { useFarmCatalog } from '../hooks/useFarmCatalog';
import { autofillAddressFromGPS } from '../hooks/useLocationAutofill';
import { completeProfileSchema, type CompleteProfileData, type CompleteProfileForm } from '../schemas';

const CREAM = '#F8F4E7';
const CARD = '#FFFDF8';
const WHITE = '#FFFFFF';
const TEXT = '#173B2B';
const MUTED = '#627067';
const GREEN = '#165B33';
const LIGHT_GREEN = '#EEF6EA';
const GOLD = '#F5B51B';
const BORDER = '#D9D6C9';

type Language = 'ta' | 'en';
type ProductForm = NonNullable<CompleteProfileForm['farmProducts']>[number];

const COPY = {
  ta: {
    steps: ['விவசாயி', 'இருப்பிடம்', 'விளைபொருட்கள்', 'FPO / KVK', 'சரிபார்ப்பு'],
    titles: ['விவசாயி விவரங்கள்', 'பண்ணை இருப்பிடம்', 'பயிர்கள் & விளைபொருட்கள்', 'ஆதரவு அமைப்புகள்', 'சரிபார்த்து சமர்ப்பிக்கவும்'],
    subtitles: ['உங்களைப் பற்றிய அடிப்படை தகவல்', 'GPS மூலம் விரைவாக நிரப்புங்கள்', 'நீங்கள் வளர்ப்பது அல்லது உற்பத்தி செய்வது', 'தேவையான உள்ளூர் ஆதரவைத் தேர்வு செய்க', 'உங்கள் விவரங்கள் சரியா என்று பாருங்கள்'],
    next: 'தொடர்க', back: 'பின்னால்', submit: 'சமர்ப்பிக்கவும்',
    phone: 'பதிவு செய்யப்பட்ட கைபேசி', farmerType: 'விவசாயி வகை', small: 'சிறு விவசாயி', tenant: 'குத்தகை விவசாயி', producer: 'விவசாய உற்பத்தியாளர்',
    gps: 'எனது இருப்பிடத்தைத் தானாக நிரப்பு', gpsHelp: 'மாவட்டம், வட்டம், கிராமம் மற்றும் GPS இடம்', detected: 'இருப்பிடம் கண்டறியப்பட்டது', landmark: 'அடையாள இடம் (விருப்பம்)',
    productPicker: 'விளைபொருட்களைச் சேர்க்கவும்', productPlaceholder: 'தேடி பலவற்றைத் தேர்வு செய்க', noProducts: 'இன்னும் விளைபொருள் சேர்க்கவில்லை', noProductsHelp: 'பயிர், காய்கறி, பழம், தோட்டப் பயிர், கால்நடை அல்லது மற்ற பொருட்களைச் சேர்க்கவும்.',
    harvest: 'எதிர்பார்க்கும் அறுவடை மாதம்', quantity: 'தோராயமான அளவு', sale: 'விற்பனைக்கு கிடைக்கும்', notSale: 'சொந்த பயன்பாடு', month: 'மாதத்தைத் தேர்வு செய்க',
    fpo: 'FPO-வைத் தேர்வு செய்க', fpoHelp: 'கூட்டு கொள்முதல், சந்தை மற்றும் உள்ளீட்டு ஆதரவு', kvk: 'KVK-வைத் தேர்வு செய்க', kvkHelp: 'பயிற்சி, செயல்விளக்கம் மற்றும் பண்ணை ஆலோசனை', both: 'சேரக் கோருவதன் மூலம், தேர்ந்தெடுத்த அமைப்புடன் உங்கள் சுயவிவரம் மற்றும் பண்ணைத் தகவல்களைப் பகிர ஒப்புக்கொள்கிறீர்கள்.',
    reviewFarmer: 'விவசாயி', reviewLocation: 'பண்ணை இருப்பிடம்', reviewProducts: 'விளைபொருட்கள்', reviewSupport: 'ஆதரவு விருப்பம்', none: 'தேர்வு செய்யவில்லை', edit: 'திருத்து',
  },
  en: {
    steps: ['Farmer', 'Location', 'Products', 'FPO / KVK', 'Review'],
    titles: ['Farmer information', 'Farm location', 'Crops & farm products', 'Support network', 'Review & submit'],
    subtitles: ['Basic information about you', 'Use GPS to fill details faster', 'What you grow or produce', 'Choose the local support you need', 'Check that your details are correct'],
    next: 'Continue', back: 'Back', submit: 'Submit profile',
    phone: 'Registered mobile', farmerType: 'Farmer type', small: 'Small farmer', tenant: 'Tenant farmer', producer: 'Farm producer',
    gps: 'Autofill my location', gpsHelp: 'District, block, village and GPS position', detected: 'Location detected', landmark: 'Nearby landmark (optional)',
    productPicker: 'Add farm products', productPlaceholder: 'Search and select multiple', noProducts: 'No products added yet', noProductsHelp: 'Add crops, vegetables, fruits, plantation crops, livestock or other farm products.',
    harvest: 'Expected harvest month', quantity: 'Approximate quantity', sale: 'Available for sale', notSale: 'For own use', month: 'Select month',
    fpo: 'Choose an FPO', fpoHelp: 'Collective buying, markets and input support', kvk: 'Choose a KVK', kvkHelp: 'Training, demonstrations and farm guidance', both: 'By requesting to join, you consent to share your profile and farm information with the selected organization.',
    reviewFarmer: 'Farmer', reviewLocation: 'Farm location', reviewProducts: 'Farm products', reviewSupport: 'Support preference', none: 'None selected', edit: 'Edit',
  },
} as const;

export function CompleteProfileScreen() {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { user } = useAuth();
  const complete = useCompleteProfile();
  const catalog = useFarmCatalog();
  const copy = COPY[language];
  const [step, setStep] = useState(0);
  const [locating, setLocating] = useState(false);
  const [districtPickerRequest, setDistrictPickerRequest] = useState(0);

  const { control, handleSubmit, watch, setValue, trigger, formState } = useForm<CompleteProfileForm, unknown, CompleteProfileData>({
    resolver: zodResolver(completeProfileSchema),
    defaultValues: {
      name: '', language, district: '', block: '', village: '', experienceYears: '', landHoldingAcres: '', preferredCrops: [], photoUrl: null,
      farmerType: null, landmark: '', latitude: null, longitude: null, farmProducts: [], wantsFpoSupport: false, wantsKvkSupport: false,
    },
    mode: 'onChange',
  });

  const products = watch('farmProducts') ?? [];
  const selectedIds = products.map((product) => product.productId);
  const district = watch('district');
  const block = watch('block');
  const village = watch('village');
  const name = watch('name');
  const farmerType = watch('farmerType');
  const wantsFpo = Boolean(watch('wantsFpoSupport'));
  const wantsKvk = Boolean(watch('wantsKvkSupport'));
  const locationDetected = watch('latitude') != null && watch('longitude') != null;
  const myLinks = useMyPartnerLinks(step === 4);

  const setProducts = (next: ProductForm[]) => {
    setValue('farmProducts', next, { shouldDirty: true, shouldValidate: true });
    const cropIds = next.filter((item) => catalog.data?.items.find((product) => product.code === item.productId)?.category !== 'livestock').map((item) => item.productId);
    setValue('preferredCrops', cropIds, { shouldDirty: true, shouldValidate: true });
  };

  const onSelectionChange = (ids: string[]) => {
    const existing = new Map(products.map((product) => [product.productId, product]));
    setProducts(ids.map((id) => existing.get(id) ?? {
      productId: id,
      category: catalog.data?.items.find((product) => product.code === id)?.category ?? catalog.data?.other_code ?? 'other',
      expectedHarvestMonth: null,
      approximateQuantity: null,
      unit: toFormUnit(catalog.data?.items.find((product) => product.code === id)?.default_unit ?? 'kg'),
      availableForSale: false,
    }));
  };

  const updateProduct = (id: string, patch: Partial<ProductForm>) => setProducts(products.map((product) => product.productId === id ? { ...product, ...patch } : product));

  const onUseMyLocation = async () => {
    if (locating) return;
    setLocating(true);
    try {
      const result = await autofillAddressFromGPS();
      if (result.status === 'permissionDenied') return Alert.alert(t('profile.locationPermissionDenied'));
      if (result.status === 'unavailable') return Alert.alert(t('profile.locationUnavailable'));
      if (result.district) setValue('district', result.district, { shouldValidate: true });
      if (result.block) setValue('block', result.block, { shouldDirty: true });
      if (result.village) setValue('village', result.village, { shouldDirty: true });
      setValue('latitude', result.latitude, { shouldDirty: true });
      setValue('longitude', result.longitude, { shouldDirty: true });
      if (result.status === 'noDistrictMatch') setDistrictPickerRequest((value) => value + 1);
    } finally { setLocating(false); }
  };

  const next = async () => {
    const valid = step === 0 ? await trigger(['name', 'experienceYears', 'landHoldingAcres']) : step === 1 ? await trigger(['district']) : true;
    if (valid) setStep((value) => Math.min(4, value + 1));
  };

  const onSubmit = handleSubmit((data) => {
    if (!complete.isPending) complete.mutate(data, { onError: () => Alert.alert(t('profile.saveFailed')) });
  });

  return (
    <AgScreen testID="complete-profile-screen" scroll keyboardAvoiding backgroundColor={CREAM} contentContainerStyle={styles.screen}>
      <StatusBar style="dark" />
      <View style={styles.topBar}>
        <View style={styles.brand} accessibilityLabel="AgrowNex">
          <Image source={require('@/assets/images/android-icon-foreground.png')} contentFit="contain" transition={0} style={styles.logo} />
          <AgText variant="headingS" weight="bold" style={styles.wordmark}>AgrowNex</AgText>
        </View>
        <AgPressable onPress={() => { const nextLanguage = language === 'ta' ? 'en' : 'ta'; setValue('language', nextLanguage); void setLanguage(nextLanguage); }} style={styles.languageButton} accessibilityRole="button">
          <AgText variant="bodySmall" weight="bold" style={styles.primary}>{language === 'ta' ? 'EN' : 'தமிழ்'}</AgText>
        </AgPressable>
      </View>

      <Progress step={step} labels={copy.steps} onPress={setStep} />
      <View style={styles.headingBlock}>
        <AgText variant="caption" weight="bold" style={styles.eyebrow}>{language === 'ta' ? `படி ${step + 1} / 5` : `STEP ${step + 1} OF 5`}</AgText>
        <AgText variant="headingL" weight="bold" style={styles.heading}>{copy.titles[step]}</AgText>
        <AgText variant="body" style={styles.subtitle}>{copy.subtitles[step]}</AgText>
      </View>

      {step === 0 ? (
        <Card icon={<UserRound size={25} color={GREEN} />}>
          {user?.phone ? <InfoLine icon={<Phone size={20} color={GREEN} />} label={copy.phone} value={user.phone} /> : null}
          <Controller control={control} name="name" render={({ field: { onChange, onBlur, value }, fieldState }) => <AgInput {...fieldTheme} label={t('profile.name')} required placeholder={t('profile.namePlaceholderRedesign')} value={value} onChangeText={onChange} onBlur={onBlur} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} leftAccessory={<UserRound size={21} color={GREEN} />} />} />
          <View style={styles.twoColumns}>
            <View style={styles.flex}><Controller control={control} name="experienceYears" render={({ field: { onChange, value }, fieldState }) => <AgInput {...fieldTheme} label={t('profile.experience')} placeholder="10" keyboardType="number-pad" value={value ?? ''} onChangeText={onChange} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} leftAccessory={<CalendarDays size={21} color={GREEN} />} />} /></View>
            <View style={styles.flex}><Controller control={control} name="landHoldingAcres" render={({ field: { onChange, value }, fieldState }) => <AgInput {...fieldTheme} label={t('profile.landHolding')} placeholder="2.5" keyboardType="decimal-pad" value={value ?? ''} onChangeText={onChange} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} leftAccessory={<Sprout size={21} color={GREEN} />} />} /></View>
          </View>
          <AgText variant="label" weight="semibold" style={styles.primary}>{copy.farmerType}</AgText>
          <View style={styles.choiceWrap}>{(['small', 'tenant', 'producer'] as const).map((type) => <Choice key={type} label={copy[type]} selected={farmerType === type} onPress={() => setValue('farmerType', type, { shouldDirty: true })} />)}</View>
        </Card>
      ) : null}

      {step === 1 ? (
        <>
          <AgPressable onPress={onUseMyLocation} disabled={locating} style={styles.gpsCard} accessibilityRole="button" accessibilityLabel={t("profile.useMyLocation")}>
            <View style={[styles.gpsIcon, locationDetected && styles.gpsIconDone]}>{locating ? <ActivityIndicator color={GREEN} /> : locationDetected ? <Check size={26} color="#FFFFFF" /> : <LocateFixed size={28} color={GREEN} />}</View>
            <View style={styles.flex}><AgText variant="bodyLarge" weight="bold" style={styles.primary}>{locationDetected ? copy.detected : copy.gps}</AgText><AgText variant="bodySmall" style={styles.muted}>{copy.gpsHelp}</AgText></View><ArrowRight size={24} color={GREEN} />
          </AgPressable>
          <Card icon={<MapPinned size={25} color={GREEN} />}>
            <Controller control={control} name="district" render={({ field: { onChange, value }, fieldState }) => <AgDistrictDropdown label={t('profile.district')} required placeholder={t('profile.selectDistrict')} value={value} openRequest={districtPickerRequest} onChange={(nextDistrict) => { if (nextDistrict !== value) { setValue('block', '', { shouldDirty: true }); setValue('village', '', { shouldDirty: true }); } onChange(nextDistrict); }} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} leftAccessory={<MapPinned size={21} color={GREEN} />} fieldStyle={styles.field} textStyle={styles.inputText} />} />
            <Controller control={control} name="block" render={({ field: { onChange, value } }) => <AgInput {...fieldTheme} label={t('profile.block')} placeholder={t('profile.blockPlaceholder')} value={value} onChangeText={onChange} leftAccessory={<MapIcon size={21} color={GREEN} />} />} />
            <Controller control={control} name="village" render={({ field: { onChange, value } }) => <AgInput {...fieldTheme} label={t('profile.village')} placeholder={t('profile.villagePlaceholder')} value={value} onChangeText={onChange} leftAccessory={<Warehouse size={21} color={GREEN} />} />} />
            <Controller control={control} name="landmark" render={({ field: { onChange, value } }) => <AgInput {...fieldTheme} label={copy.landmark} placeholder={language === 'ta' ? 'எ.கா. கோவில் அருகில்' : 'e.g. near temple'} value={value} onChangeText={onChange} leftAccessory={<Landmark size={21} color={GREEN} />} />} />
          </Card>
        </>
      ) : null}

      {step === 2 ? (
        <Card icon={<PackageOpen size={25} color={GREEN} />}>
          {catalog.isLoading ? <AgSpinner /> : catalog.isError || !catalog.data ? <CatalogError language={language} onRetry={() => void catalog.refetch()} /> : <ProductMultiSelect language={language} selectedIds={selectedIds} onChange={onSelectionChange} label={copy.productPicker} placeholder={copy.productPlaceholder} products={catalog.data.items} categories={catalog.data.categories} />}
          {!products.length ? <View style={styles.emptyState}><Sprout size={34} color="#75A270" /><AgText variant="body" weight="bold" style={styles.primary}>{copy.noProducts}</AgText><AgText variant="bodySmall" style={styles.centerMuted}>{copy.noProductsHelp}</AgText></View> : products.map((product) => <ProductDetails key={product.productId} language={language} copy={copy} product={product} catalogItems={catalog.data?.items ?? []} onChange={(patch) => updateProduct(product.productId, patch)} onRemove={() => setProducts(products.filter((item) => item.productId !== product.productId))} />)}
        </Card>
      ) : null}

      {step === 3 ? (
        <Card icon={<Building2 size={25} color={GREEN} />}>
          <AgText variant="bodySmall" style={styles.consent}>{copy.both}</AgText>
          <OrganizationDirectory kind="fpo" district={district} language={language} title={copy.fpo} description={copy.fpoHelp} icon={<Building2 size={25} color={GREEN} />} onJoined={() => setValue('wantsFpoSupport', true, { shouldDirty: true })} />
          <OrganizationDirectory kind="kvk" district={district} language={language} title={copy.kvk} description={copy.kvkHelp} icon={<GraduationCap size={25} color={GREEN} />} onJoined={() => setValue('wantsKvkSupport', true, { shouldDirty: true })} />
        </Card>
      ) : null}

      {step === 4 ? (
        <View style={styles.reviewList}>
          <ReviewCard title={copy.reviewFarmer} value={`${name || '—'}${farmerType ? ` · ${copy[farmerType as 'small' | 'tenant' | 'producer']}` : ''}`} onPress={() => setStep(0)} copy={copy} />
          <ReviewCard title={copy.reviewLocation} value={locationSummary(village, block, district, language)} onPress={() => setStep(1)} copy={copy} />
          <ReviewCard title={copy.reviewProducts} value={products.length ? products.map((product) => productLabel(catalog.data?.items ?? [], product.productId, language)).join(', ') : copy.none} onPress={() => setStep(2)} copy={copy} />
          <ReviewCard title={copy.reviewSupport} value={supportSummary(myLinks.data ?? [], language) || [wantsFpo && 'FPO', wantsKvk && 'KVK'].filter(Boolean).join(' + ') || copy.none} onPress={() => setStep(3)} copy={copy} />
          <View style={styles.usefulNote}><Sprout size={22} color={GREEN} /><AgText variant="bodySmall" style={styles.primary}>{language === 'ta' ? 'இந்த விவரங்கள் பயிர் வரைபடம், கொள்முதல் திட்டம், பயிற்சி மற்றும் விவசாயி ஆதரவுக்கு உதவும்.' : 'These details support crop mapping, procurement planning, training and farmer support.'}</AgText></View>
        </View>
      ) : null}

      <View style={styles.actions}>
        {step > 0 ? <AgPressable onPress={() => setStep((value) => value - 1)} style={styles.backButton}><ArrowLeft size={22} color={GREEN} /><AgText variant="body" weight="bold" style={styles.primary}>{copy.back}</AgText></AgPressable> : null}
        <AgPressable testID={step === 4 ? 'finish-setup-button' : 'onboarding-next-button'} onPress={step === 4 ? onSubmit : next} disabled={complete.isPending || (step === 4 && !formState.isValid)} style={styles.nextButton} accessibilityRole="button">
          {complete.isPending ? <ActivityIndicator color={TEXT} /> : <><AgText variant="bodyLarge" weight="bold" style={styles.primary}>{step === 4 ? copy.submit : copy.next}</AgText><ArrowRight size={23} color={TEXT} /></>}
        </AgPressable>
      </View>
    </AgScreen>
  );
}

function Progress({ step, labels, onPress }: { step: number; labels: readonly string[]; onPress: (step: number) => void }) {
  return <View style={styles.progress}>{labels.map((label, index) => <View key={label} style={styles.progressItem}><AgPressable disabled={index > step} onPress={() => onPress(index)} style={[styles.stepCircle, index < step && styles.stepDone, index === step && styles.stepCurrent]}>{index < step ? <Check size={16} color="#FFFFFF" strokeWidth={3} /> : <AgText variant="caption" weight="bold" style={index === step ? styles.currentStepText : styles.stepText}>{index + 1}</AgText>}</AgPressable><AgText variant="caption" weight={index === step ? 'bold' : 'medium'} numberOfLines={2} style={[styles.stepLabel, index === step && styles.stepLabelActive]}>{label}</AgText>{index < 4 ? <View style={[styles.stepLine, index < step && styles.stepLineDone]} /> : null}</View>)}</View>;
}

function Card({ icon, children }: { icon: ReactNode; children: ReactNode }) { return <View style={styles.card}><View style={styles.cardIcon}>{icon}</View><View style={styles.cardContent}>{children}</View></View>; }
function Choice({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) { return <AgPressable onPress={onPress} accessibilityRole="radio" accessibilityState={{ checked: selected }} style={[styles.choice, selected && styles.choiceSelected]}>{selected ? <Check size={16} color="#FFFFFF" /> : null}<AgText variant="bodySmall" weight="semibold" style={selected ? styles.whiteText : styles.primary}>{label}</AgText></AgPressable>; }
function InfoLine({ icon, label, value }: { icon: ReactNode; label: string; value: string }) { return <View style={styles.infoLine}>{icon}<View><AgText variant="caption" style={styles.muted}>{label}</AgText><AgText variant="body" weight="semibold" style={styles.primary}>{value}</AgText></View></View>; }

function ProductDetails({ language, copy, product, catalogItems, onChange, onRemove }: { language: Language; copy: typeof COPY.ta | typeof COPY.en; product: ProductForm; catalogItems: OnboardingProductOption[]; onChange: (patch: Partial<ProductForm>) => void; onRemove: () => void }) {
  return <View style={styles.productCard}>
    <View style={styles.productHeader}><View style={styles.productBadge}><Sprout size={21} color={GREEN} /></View><View style={styles.flex}><AgText variant="bodyLarge" weight="bold" style={styles.primary}>{productLabel(catalogItems, product.productId, language)}</AgText><AgText variant="caption" style={styles.muted}>{productLabel(catalogItems, product.productId, language === 'ta' ? 'en' : 'ta')}</AgText></View><AgPressable onPress={onRemove} accessibilityRole="button" style={styles.removeButton}><Trash2 size={20} color="#A43E35" /></AgPressable></View>
    <MonthPicker language={language} value={product.expectedHarvestMonth} label={copy.harvest} placeholder={copy.month} onChange={(value) => onChange({ expectedHarvestMonth: value })} />
    <View style={styles.quantityRow}><QuantityInput value={product.approximateQuantity} placeholder={copy.quantity} onChange={(value) => onChange({ approximateQuantity: value })} /><AgPressable onPress={() => onChange({ unit: nextUnit(product.unit) })} style={styles.unitButton}><AgText variant="bodySmall" weight="bold" style={styles.primary}>{product.unit}</AgText><ChevronDown size={17} color={GREEN} /></AgPressable></View>
    <AgPressable onPress={() => onChange({ availableForSale: !product.availableForSale })} style={[styles.saleToggle, product.availableForSale && styles.saleToggleActive]} accessibilityRole="switch" accessibilityState={{ checked: product.availableForSale }}><View style={[styles.switchTrack, product.availableForSale && styles.switchTrackActive]}><View style={[styles.switchThumb, product.availableForSale && styles.switchThumbActive]} /></View><AgText variant="bodySmall" weight="semibold" style={styles.primary}>{product.availableForSale ? copy.sale : copy.notSale}</AgText></AgPressable>
  </View>;
}

/** Keeps the typed text (e.g. "2.") so decimals can be entered; reports a number or null. */
function QuantityInput({ value, placeholder, onChange }: { value: number | null | undefined; placeholder: string; onChange: (value: number | null) => void }) {
  const [text, setText] = useState(value == null ? '' : String(value));
  return <TextInput value={text} onChangeText={(raw) => {
    const cleaned = raw.replace(/,/g, '.').replace(/[^0-9.]/g, '').replace(/(\..*)\./g, '$1');
    setText(cleaned);
    const parsed = Number(cleaned);
    onChange(cleaned && cleaned !== '.' && Number.isFinite(parsed) ? parsed : null);
  }} placeholder={placeholder} placeholderTextColor={MUTED} keyboardType="decimal-pad" style={styles.quantityInput} />;
}

function MonthPicker({ language, value, label, placeholder, onChange }: { language: Language; value: string | null; label: string; placeholder: string; onChange: (value: string) => void }) {
  const [visible, setVisible] = useState(false);
  const months = useMemo(() => Array.from({ length: 18 }, (_, index) => { const date = new Date(); date.setDate(1); date.setMonth(date.getMonth() + index); return { value: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`, label: new Intl.DateTimeFormat(language === 'ta' ? 'ta-IN' : 'en-IN', { month: 'long', year: 'numeric' }).format(date) }; }), [language]);
  const selected = months.find((month) => month.value === value);
  return <><AgText variant="caption" weight="semibold" style={styles.primary}>{label}</AgText><AgPressable onPress={() => setVisible(true)} style={styles.monthField}><CalendarDays size={20} color={GREEN} /><AgText variant="bodySmall" style={selected ? styles.primary : styles.muted}>{selected?.label ?? placeholder}</AgText><ChevronDown size={19} color={GREEN} /></AgPressable><Modal transparent visible={visible} animationType="fade" onRequestClose={() => setVisible(false)}><View style={styles.modalBackdrop}><SafeAreaView style={styles.monthModal}><ScrollView>{months.map((month) => <AgPressable key={month.value} onPress={() => { onChange(month.value); setVisible(false); }} style={[styles.monthRow, value === month.value && styles.monthRowSelected]}><AgText variant="body" weight={value === month.value ? 'bold' : 'medium'} style={styles.primary}>{month.label}</AgText>{value === month.value ? <Check size={20} color={GREEN} /> : null}</AgPressable>)}</ScrollView></SafeAreaView></View></Modal></>;
}

function CatalogError({ language, onRetry, message }: { language: Language; onRetry: () => void; message?: string }) {
  return <View style={styles.inlineError}><AgText variant="bodySmall" style={styles.centerMuted}>{message ?? (language === 'ta' ? 'விளைபொருள் பட்டியலை ஏற்ற முடியவில்லை.' : 'Could not load the farm product list.')}</AgText><AgPressable onPress={onRetry} style={styles.retryButton}><AgText variant="bodySmall" weight="bold" style={styles.primary}>{language === 'ta' ? 'மீண்டும் முயல்க' : 'Try again'}</AgText></AgPressable></View>;
}

function OrganizationDirectory({ kind, district, language, title, description, icon, onJoined }: { kind: 'fpo' | 'kvk'; district: string; language: Language; title: string; description: string; icon: ReactNode; onJoined: () => void }) {
  const directory = usePartnerDirectory(kind, district, Boolean(district));
  const links = useMyPartnerLinks(Boolean(district));
  const join = useJoinPartnerOrganization();

  const requestJoin = (organizationId: string) => join.mutate(organizationId, {
    onSuccess: onJoined,
    onError: () => Alert.alert(language === 'ta' ? 'கோரிக்கையை அனுப்ப முடியவில்லை' : 'Could not send request', language === 'ta' ? 'மீண்டும் முயற்சிக்கவும்.' : 'Please try again.'),
  });

  return <View style={styles.directorySection}>
    <View style={styles.directoryHeader}><View style={styles.supportIcon}>{icon}</View><View style={styles.flex}><AgText variant="body" weight="bold" style={styles.primary}>{title}</AgText><AgText variant="bodySmall" style={styles.muted}>{description}</AgText></View></View>
    {directory.isLoading || links.isLoading ? <AgSpinner /> : directory.isError || links.isError ? <CatalogError language={language} message={language === 'ta' ? 'அமைப்புகளின் பட்டியலை ஏற்ற முடியவில்லை.' : 'Could not load organizations.'} onRetry={() => { void directory.refetch(); void links.refetch(); }} /> : !directory.data?.length ? <AgText variant="bodySmall" style={styles.centerMuted}>{language === 'ta' ? 'இந்த மாவட்டத்தில் அமைப்பு கிடைக்கவில்லை.' : 'No organization is listed for this district yet.'}</AgText> : directory.data.map((organization) => {
      const link = links.data?.find((item) => item.organizationId === organization.id && item.status !== 'revoked');
      const status = link?.status === 'active' ? (language === 'ta' ? 'உறுப்பினர்' : 'Member') : link?.status === 'join_requested' ? (language === 'ta' ? 'காத்திருக்கிறது' : 'Waiting') : link?.status === 'pending' ? (language === 'ta' ? 'அழைப்பு வந்துள்ளது' : 'Invite received') : null;
      return <View key={organization.id} style={styles.organizationRow}><View><AgText variant="body" weight="semibold" style={styles.primary}>{organization.name}</AgText><AgText variant="caption" style={styles.muted}>{organization.district ?? district}</AgText></View>{status ? <View style={styles.statusPill}><AgText variant="caption" weight="bold" style={styles.greenText}>{status}</AgText></View> : <AgPressable onPress={() => requestJoin(organization.id)} disabled={join.isPending} style={styles.joinButton}>{join.isPending ? <ActivityIndicator color={TEXT} /> : <AgText variant="bodySmall" weight="bold" style={styles.primary}>{language === 'ta' ? 'சேரக் கோரு' : 'Request to join'}</AgText>}</AgPressable>}</View>;
    })}
  </View>;
}
function ReviewCard({ title, value, onPress, copy }: { title: string; value: string; onPress: () => void; copy: typeof COPY.ta | typeof COPY.en }) { return <View style={styles.reviewCard}><View style={styles.flex}><AgText variant="caption" weight="bold" style={styles.muted}>{title}</AgText><AgText variant="body" weight="semibold" style={styles.primary}>{value}</AgText></View><AgPressable onPress={onPress} style={styles.editButton}><AgText variant="bodySmall" weight="bold" style={styles.greenText}>{copy.edit}</AgText></AgPressable></View>; }
/** Village, block, district without repeats (e.g. "Thoothukudi, thoothukudi"), district by its proper name. */
function locationSummary(village: string | undefined, block: string | undefined, districtId: string | undefined, language: Language): string {
  const districtName = TAMIL_NADU_DISTRICTS.find((item) => item.id === districtId)?.[language] ?? districtId ?? "";
  const parts: string[] = [];
  for (const part of [village, block, districtName]) {
    const text = part?.trim();
    if (text && !parts.some((existing) => existing.toLowerCase() === text.toLowerCase())) parts.push(text);
  }
  return parts.join(', ') || '—';
}

/** Organizations the farmer asked to join / is a member of, with status. */
function supportSummary(links: PartnerLinkRequest[], language: Language): string {
  const label = (status: PartnerLinkRequest['status']) => status === 'active' ? (language === 'ta' ? 'உறுப்பினர்' : 'member') : status === 'join_requested' ? (language === 'ta' ? 'காத்திருக்கிறது' : 'waiting') : status === 'pending' ? (language === 'ta' ? 'அழைப்பு' : 'invited') : null;
  return links.filter((link) => label(link.status)).map((link) => `${link.organizationName} (${label(link.status)})`).join('\n');
}

function nextUnit(unit: ProductForm['unit']): ProductForm['unit'] { const units: ProductForm['unit'][] = ['kg', 'quintal', 'tonne', 'bag', 'count', 'litre']; return units[(units.indexOf(unit) + 1) % units.length]; }

const fieldTheme = { fieldStyle: { minHeight: 58, borderRadius: 14, borderWidth: 1.3, borderColor: BORDER, backgroundColor: WHITE }, fieldBorderColor: BORDER, fieldBackgroundColor: WHITE, focusBorderColor: GREEN, style: { color: TEXT, backgroundColor: 'transparent' }, placeholderTextColor: MUTED } as const;

const styles = StyleSheet.create({
  screen: { flexGrow: 1, paddingTop: 4, paddingBottom: 24 }, topBar: { minHeight: 62, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, brand: { flexDirection: 'row', alignItems: 'center' }, logo: { width: 54, height: 54 }, wordmark: { marginLeft: -5, color: GREEN, letterSpacing: -0.7 }, languageButton: { minWidth: 54, minHeight: 44, borderWidth: 1, borderColor: '#C6CDBD', borderRadius: 22, backgroundColor: CARD, alignItems: 'center', justifyContent: 'center' },
  progress: { marginTop: 10, flexDirection: 'row', justifyContent: 'space-between' }, progressItem: { width: '20%', alignItems: 'center', position: 'relative' }, stepCircle: { width: 34, height: 34, borderRadius: 17, borderWidth: 1.4, borderColor: '#C8C7BD', backgroundColor: '#F0EEE5', alignItems: 'center', justifyContent: 'center', zIndex: 2 }, stepDone: { borderColor: '#4E9B45', backgroundColor: '#4E9B45' }, stepCurrent: { borderColor: GOLD, backgroundColor: GOLD }, stepLine: { position: 'absolute', top: 16, left: '68%', width: '64%', height: 2, backgroundColor: '#D5D2C8' }, stepLineDone: { backgroundColor: '#4E9B45' }, stepText: { color: MUTED }, currentStepText: { color: TEXT }, stepLabel: { width: '100%', marginTop: 5, color: MUTED, textAlign: 'center', fontSize: 10 }, stepLabelActive: { color: TEXT },
  headingBlock: { marginTop: 26, marginBottom: 18 }, eyebrow: { color: '#A16207', letterSpacing: 0.7 }, heading: { marginTop: 7, color: TEXT, lineHeight: 39 }, subtitle: { marginTop: 7, color: MUTED, lineHeight: 22 }, primary: { color: TEXT }, muted: { color: MUTED }, greenText: { color: GREEN }, whiteText: { color: '#FFFFFF' }, flex: { flex: 1, minWidth: 0 }, centerMuted: { color: MUTED, textAlign: 'center', lineHeight: 20 },
  card: { position: 'relative', borderWidth: 1, borderColor: '#E3DED0', borderRadius: 22, backgroundColor: CARD, padding: 17, shadowColor: TEXT, shadowOpacity: 0.07, shadowRadius: 9, shadowOffset: { width: 0, height: 3 }, elevation: 2 }, cardIcon: { position: 'absolute', top: -14, left: 17, width: 48, height: 48, borderRadius: 24, backgroundColor: '#F7F1D9', borderWidth: 5, borderColor: CREAM, alignItems: 'center', justifyContent: 'center', zIndex: 2 }, cardContent: { paddingTop: 23, gap: 15 }, field: { minHeight: 58, borderRadius: 14, borderWidth: 1.3, borderColor: BORDER, backgroundColor: WHITE }, inputText: { color: TEXT },
  infoLine: { minHeight: 58, paddingHorizontal: 14, borderRadius: 14, backgroundColor: LIGHT_GREEN, flexDirection: 'row', alignItems: 'center', gap: 12 }, twoColumns: { flexDirection: 'row', gap: 10 }, choiceWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, choice: { minHeight: 46, paddingHorizontal: 14, borderWidth: 1, borderColor: BORDER, borderRadius: 23, backgroundColor: WHITE, flexDirection: 'row', alignItems: 'center', gap: 7 }, choiceSelected: { borderColor: GREEN, backgroundColor: GREEN },
  gpsCard: { minHeight: 92, marginBottom: 16, paddingHorizontal: 16, borderWidth: 1.2, borderColor: '#A7C6A2', borderRadius: 20, backgroundColor: LIGHT_GREEN, flexDirection: 'row', alignItems: 'center', gap: 13 }, gpsIcon: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#DCEFD9', alignItems: 'center', justifyContent: 'center' }, gpsIconDone: { backgroundColor: GREEN },
  emptyState: { minHeight: 176, borderWidth: 1, borderStyle: 'dashed', borderColor: '#B7C9B1', borderRadius: 17, backgroundColor: '#F6FAF3', paddingHorizontal: 24, alignItems: 'center', justifyContent: 'center', gap: 8 }, productCard: { borderWidth: 1, borderColor: '#CAD8C4', borderRadius: 18, backgroundColor: '#F8FBF5', padding: 14, gap: 10 }, productHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 }, productBadge: { width: 42, height: 42, borderRadius: 21, backgroundColor: '#E4F2DF', alignItems: 'center', justifyContent: 'center' }, removeButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#FBEDE9', alignItems: 'center', justifyContent: 'center' }, monthField: { minHeight: 52, paddingHorizontal: 13, borderWidth: 1, borderColor: BORDER, borderRadius: 13, backgroundColor: WHITE, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }, quantityRow: { minHeight: 54, borderWidth: 1, borderColor: BORDER, borderRadius: 13, overflow: 'hidden', backgroundColor: WHITE, flexDirection: 'row' }, quantityInput: { flex: 1, paddingHorizontal: 14, color: TEXT, fontSize: 16 }, unitButton: { minWidth: 92, borderLeftWidth: 1, borderLeftColor: BORDER, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5 }, saleToggle: { minHeight: 52, paddingHorizontal: 13, borderRadius: 13, backgroundColor: '#F0EFEA', flexDirection: 'row', alignItems: 'center', gap: 10 }, saleToggleActive: { backgroundColor: '#E5F3DF' }, switchTrack: { width: 46, height: 26, borderRadius: 13, backgroundColor: '#A8ADA7', padding: 3 }, switchTrackActive: { backgroundColor: GREEN }, switchThumb: { width: 20, height: 20, borderRadius: 10, backgroundColor: WHITE }, switchThumbActive: { marginLeft: 20 },
  inlineError: { minHeight: 94, borderWidth: 1, borderColor: '#E4C5BC', borderRadius: 16, backgroundColor: '#FFF7F3', padding: 14, alignItems: 'center', justifyContent: 'center', gap: 9 }, retryButton: { minHeight: 44, borderRadius: 22, backgroundColor: '#F3C34D', paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center' },
  modalBackdrop: { flex: 1, paddingHorizontal: 24, justifyContent: 'center', backgroundColor: 'rgba(10,30,20,0.5)' }, monthModal: { maxHeight: '78%', borderRadius: 22, backgroundColor: CARD, padding: 10 }, monthRow: { minHeight: 52, borderRadius: 12, paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, monthRowSelected: { backgroundColor: LIGHT_GREEN },
  supportCard: { minHeight: 94, padding: 14, borderWidth: 1.2, borderColor: BORDER, borderRadius: 18, backgroundColor: WHITE, flexDirection: 'row', alignItems: 'center', gap: 13 }, supportSelected: { borderColor: '#5F9B59', backgroundColor: LIGHT_GREEN }, supportIcon: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#F0F5E7', alignItems: 'center', justifyContent: 'center' }, largeCheck: { width: 28, height: 28, borderRadius: 9, borderWidth: 1.5, borderColor: '#A8ADA7', alignItems: 'center', justifyContent: 'center' }, largeCheckSelected: { borderColor: GREEN, backgroundColor: GREEN }, consent: { color: MUTED, lineHeight: 20, textAlign: 'center', paddingHorizontal: 8 },
  directorySection: { borderWidth: 1, borderColor: '#CAD8C4', borderRadius: 18, backgroundColor: '#F8FBF5', padding: 13, gap: 10 }, directoryHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 }, organizationRow: { borderWidth: 1, borderColor: BORDER, borderRadius: 14, backgroundColor: WHITE, paddingHorizontal: 14, paddingVertical: 12, gap: 10 }, joinButton: { minHeight: 48, borderRadius: 14, backgroundColor: GOLD, paddingHorizontal: 12, alignItems: 'center', justifyContent: 'center' }, statusPill: { alignSelf: 'flex-start', minHeight: 36, borderRadius: 18, backgroundColor: LIGHT_GREEN, paddingHorizontal: 14, alignItems: 'center', justifyContent: 'center' },
  reviewList: { gap: 11 }, reviewCard: { minHeight: 84, padding: 15, borderWidth: 1, borderColor: '#E0DCCF', borderRadius: 18, backgroundColor: CARD, flexDirection: 'row', alignItems: 'center', gap: 12 }, editButton: { minWidth: 58, minHeight: 44, borderRadius: 22, backgroundColor: LIGHT_GREEN, alignItems: 'center', justifyContent: 'center' }, usefulNote: { padding: 14, borderRadius: 16, backgroundColor: '#EAF4E4', flexDirection: 'row', alignItems: 'center', gap: 10 },
  actions: { marginTop: 18, flexDirection: 'row', gap: 10 }, backButton: { minHeight: 58, paddingHorizontal: 17, borderWidth: 1.3, borderColor: '#9AAF9D', borderRadius: 17, backgroundColor: CARD, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }, nextButton: { flex: 1, minHeight: 58, borderRadius: 17, backgroundColor: GOLD, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
});
