import { zodResolver } from '@hookform/resolvers/zod';
import dayjs from 'dayjs';
import { Image } from 'expo-image';
import { Camera, Plus, X } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, Switch, TouchableOpacity, View } from 'react-native';

import {
  AgButton,
  AgChip,
  AgDropdown as BaseAgDropdown,
  type AgDropdownProps,
  AgInput as BaseAgInput,
  type AgInputProps,
  AgText,
} from '@/components/ui';
import { uploadService } from '@/features/profile/services/uploadProvider';
import { useFarms } from '@/features/farm';
import { pickPhoto } from '@/utils/image';

import { GRADES, GRADE_LABEL_KEY, UNITS, UNIT_LABEL_KEY, FARMER_SETTABLE_STATUSES, STATUS_LABEL_KEY, LISTING_TYPE_LABEL_KEY, PRODUCE_CATEGORIES, PRODUCE_LISTING_TYPES, PRODUCE_PRODUCTS, resolveProduceProduct } from '../constants';
import { produceFormSchema, type ProduceFormData, type ProduceFormInput } from '../schemas';
import type { ProduceImageInput, ProduceInput, ProduceOfferDetail } from '../types';
import { PRODUCE_COLORS as C } from '../produceTheme';

/** Clean commodity term for market matching, e.g. "Paddy (Rice)" → "Paddy". */
function cleanCrop(en: string): string {
  return en.replace(/\s*\(.*\)\s*/, '').trim();
}

const ACRES_PER_HECTARE = 2.4710538147;

/** The produce flow is intentionally fixed-light for outdoor readability. */
function AgInput(props: AgInputProps) {
  return <BaseAgInput {...props} light />;
}

function AgDropdown(props: AgDropdownProps) {
  return <BaseAgDropdown {...props} light />;
}

export function ProduceForm({
  mode,
  initial,
  submitting,
  errorKey,
  showPhotos = false,
  onSubmit,
}: {
  mode: 'create' | 'edit';
  initial?: ProduceOfferDetail;
  submitting: boolean;
  errorKey?: string;
  showPhotos?: boolean;
  onSubmit: (input: ProduceInput) => void;
}) {
  const { t } = useTranslation();

  const { data: farmsData } = useFarms();
  const farms = farmsData?.items ?? [];

  const [images, setImages] = useState<ProduceImageInput[]>([]);
  const [uploading, setUploading] = useState(false);

  const farmOptions = farms.map((f) => ({ value: f.id, label: f.name }));
  const categoryOptions = PRODUCE_CATEGORIES.map((item) => ({ value: item.value, label: t(item.labelKey) }));
  const unitOptions = UNITS.map((u) => ({ value: u, label: t(UNIT_LABEL_KEY[u]) }));
  const gradeOptions = GRADES.map((g) => ({ value: g, label: t(GRADE_LABEL_KEY[g]) }));
  const statusOptions = FARMER_SETTABLE_STATUSES.map((s) => ({
    value: s,
    label: t(STATUS_LABEL_KEY[s]),
  }));

  const { control, getValues, handleSubmit, setValue, watch } = useForm<
    ProduceFormInput,
    unknown,
    ProduceFormData
  >({
    resolver: zodResolver(produceFormSchema),
    defaultValues: {
      farmId: initial?.farmId ?? farms[0]?.id ?? '',
      availabilityType: initial?.availabilityType ?? 'available_now',
      category: initial?.category ?? 'grains',
      productName: initial?.productName ?? initial?.cropName ?? '',
      customProductName: initial?.customProductName ?? '',
      cropName: initial?.cropName ?? (farms[0]?.crop ? cleanCrop(farms[0].crop) : ''),
      variety: initial?.variety ?? '',
      cultivatedAreaAcres: initial?.cultivatedAreaHectares
        ? String(Number((initial.cultivatedAreaHectares * ACRES_PER_HECTARE).toFixed(2)))
        : '',
      expectedTotalQuantity: initial?.expectedTotalQuantity
        ? String(initial.expectedTotalQuantity)
        : initial ? String(initial.quantity) : '',
      availableQuantity: initial?.availableQuantity
        ? String(initial.availableQuantity)
        : initial ? String(initial.quantity) : '',
      unit: initial?.unit ?? 'quintal',
      expectedHarvestDate: initial?.expectedHarvestDate ?? '',
      availableFrom: initial?.availableFrom ?? initial?.expectedHarvestDate ?? '',
      availableUntil: initial?.availableUntil ?? initial?.expectedHarvestDate ?? '',
      expectedGrade: initial?.expectedGrade ?? undefined,
      askingPrice: initial?.askingPrice != null ? String(initial.askingPrice) : '',
      priceUnit: initial?.priceUnit ?? initial?.unit ?? 'quintal',
      negotiable: initial?.negotiable ?? false,
      packaging: initial?.packaging ?? '',
      pickupLocation: initial?.pickupLocation ?? '',
      notes: initial?.notes ?? '',
      qualityNotes: initial?.qualityNotes ?? '',
      status: (initial?.status as ProduceFormInput['status']) ?? 'submitted',
    },
  });

  // Farms arrive asynchronously. useForm only consumes defaultValues on its
  // first render, so a new listing could stay stuck with an empty farm/crop
  // even after the farmer's farms had loaded.
  useEffect(() => {
    if (mode !== 'create' || farms.length === 0) return;
    const firstFarm = farms[0];
    if (!getValues('farmId')) {
      setValue('farmId', firstFarm.id, { shouldValidate: true });
    }
    if (!getValues('cropName') && firstFarm.crop) {
      setValue('cropName', cleanCrop(firstFarm.crop), { shouldValidate: true });
    }
  }, [farms, getValues, mode, setValue]);

  const harvestDate = watch('expectedHarvestDate');
  const availabilityType = watch('availabilityType');
  const category = watch('category');
  const productOptions = category === 'other_produce'
    ? [{ value: 'Other', label: t('produce.categoryOther') }]
    : (PRODUCE_PRODUCTS[category] ?? []).map((name) => ({ value: name, label: name }));

  const setQuickDate = (days: number) => {
    setValue('expectedHarvestDate', dayjs().add(days, 'day').format('YYYY-MM-DD'), {
      shouldValidate: true,
    });
    setValue('availableFrom', dayjs().add(days, 'day').format('YYYY-MM-DD'), { shouldValidate: true });
    setValue('availableUntil', dayjs().add(days + 3, 'day').format('YYYY-MM-DD'), { shouldValidate: true });
  };

  const addPhoto = async () => {
    const uri = await pickPhoto();
    if (!uri) return;
    setUploading(true);
    try {
      const url = await uploadService.uploadImage(uri, 'produce');
      setImages((prev) => [...prev, { imageUrl: url, mimeType: 'image/jpeg' }]);
    } catch {
      Alert.alert(t('produce.uploadFailed'));
    } finally {
      setUploading(false);
    }
  };

  const submit = handleSubmit((data) => {
    const product = resolveProduceProduct(data.category, data.productName, data.customProductName);
    if (!product) return;
    const input: ProduceInput = {
      farmId: data.farmId,
      cropName: product,
      availabilityType: data.availabilityType,
      category: data.category,
      productName: product,
      customProductName: data.category === 'other_produce' ? product : null,
      variety: data.variety || null,
      quantity: data.availableQuantity,
      unit: data.unit,
      cultivatedAreaAcres: data.cultivatedAreaAcres,
      expectedTotalQuantity: data.expectedTotalQuantity,
      availableQuantity: data.availableQuantity,
      qualityNotes: data.qualityNotes,
      expectedHarvestDate: data.availabilityType === 'upcoming_harvest' ? data.expectedHarvestDate : null,
      availableFrom: data.availableFrom,
      availableUntil: data.availableUntil,
      expectedGrade: data.expectedGrade ?? null,
      askingPrice: data.askingPrice,
      priceUnit: data.priceUnit,
      negotiable: data.negotiable,
      packaging: data.packaging || null,
      pickupLocation: data.pickupLocation || null,
      notes: data.notes || null,
      status: data.category === 'other_produce' ? 'draft' : data.status,
      images: showPhotos ? images : undefined,
    };
    onSubmit(input);
  });

  if (farms.length === 0) {
    return (
      <View style={styles.noFarmCard}>
        <AgText variant="bodyLarge" weight="bold" style={styles.ink}>
          {t('produce.noFarmTitle')}
        </AgText>
        <AgText variant="body" color="muted" style={styles.muted}>
          {t('produce.noFarmMessage')}
        </AgText>
      </View>
    );
  }

  return (
    <View style={styles.form}>
      <View accessibilityRole="radiogroup" style={styles.availabilityCard}>
        <AgText variant="label" weight="bold" style={styles.sectionLabel}>{t('produce.listingType')}</AgText>
        <View style={styles.segmentRow}>
          {PRODUCE_LISTING_TYPES.map((type) => (
            <TouchableOpacity
              key={type}
              activeOpacity={0.78}
              onPress={() => setValue('availabilityType', type, { shouldValidate: true })}
              accessibilityRole="radio"
              accessibilityState={{ checked: availabilityType === type }}
              style={[
                styles.segment,
                availabilityType === type ? styles.segmentSelected : styles.segmentIdle,
              ]}
            >
              <AgText weight="semibold" center style={{ color: availabilityType === type ? C.paper : C.ink }}>{t(LISTING_TYPE_LABEL_KEY[type])}</AgText>
            </TouchableOpacity>
          ))}
        </View>
      </View>
      <Controller
        control={control}
        name="farmId"
        render={({ field: { onChange, value }, fieldState }) => (
          <AgDropdown
            label={t('produce.farm')}
            title={t('produce.farm')}
            placeholder={t('produce.selectFarm')}
            value={value}
            options={farmOptions}
            onChange={onChange}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
      />

      {availabilityType === 'upcoming_harvest' ? <Controller
        control={control}
        name="cultivatedAreaAcres"
        render={({ field: { onChange, onBlur, value }, fieldState }) => (
          <AgInput
            label={t('produce.cultivatedArea')}
            hint={t('produce.cultivatedAreaHint')}
            placeholder="0"
            keyboardType="decimal-pad"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
      /> : null}

      <Controller
        control={control}
        name="expectedTotalQuantity"
        render={({ field: { onChange, onBlur, value }, fieldState }) => (
          <AgInput
            label={t('produce.expectedTotalQuantity')}
            placeholder="0"
            keyboardType="decimal-pad"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
      />

      <View style={styles.twoColumn}>
        <View style={styles.flex}>
          <Controller
        control={control}
        name="availableQuantity"
        render={({ field: { onChange, onBlur, value }, fieldState }) => (
          <AgInput
            label={t('produce.availableQuantity')}
            placeholder="0"
            keyboardType="decimal-pad"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
          />
        </View>
        <View style={styles.flex}>
          <Controller
            control={control}
            name="unit"
            render={({ field: { onChange, value } }) => (
              <AgDropdown label={t('produce.unit')} title={t('produce.unit')} placeholder={t('produce.unit')} value={value} options={unitOptions} onChange={onChange} />
            )}
          />
        </View>
      </View>

      <Controller
        control={control}
        name="category"
        render={({ field: { onChange, value }, fieldState }) => (
          <AgDropdown
            label={t('produce.category')}
            title={t('produce.selectCategory')}
            placeholder={t('produce.selectCategory')}
            value={value}
            options={categoryOptions}
            onChange={(next) => { onChange(next); setValue('productName', next === 'other_produce' ? 'Other' : ''); setValue('customProductName', ''); }}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
      />

      <Controller control={control} name="productName" render={({ field: { onChange, value }, fieldState }) => (
        <AgDropdown searchable label={t('produce.product')} title={t('produce.selectProduct')} placeholder={t('produce.selectProduct')} value={value} options={productOptions} onChange={onChange} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} />
      )} />

      {category === 'other_produce' ? <Controller control={control} name="customProductName" render={({ field: { onChange, onBlur, value }, fieldState }) => (
        <AgInput label={t('produce.customProduct')} placeholder={t('produce.customProductPlaceholder')} value={value} onChangeText={onChange} onBlur={onBlur} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} />
      )} /> : null}

      <Controller
        control={control}
        name="variety"
        render={({ field: { onChange, onBlur, value } }) => (
          <AgInput
            label={t('produce.variety')}
            placeholder={t('produce.varietyPlaceholder')}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
          />
        )}
      />

      {availabilityType === 'upcoming_harvest' ? <View>
        <Controller
          control={control}
          name="expectedHarvestDate"
          render={({ field: { onChange, onBlur, value }, fieldState }) => (
            <AgInput
              label={t('produce.expectedHarvest')}
              placeholder="YYYY-MM-DD"
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
            />
          )}
        />
        <View style={styles.quickDates}>
          {[7, 15, 30].map((d) => (
            <AgChip
              key={d}
              label={t('produce.inDaysChip', { count: d })}
              selected={harvestDate === dayjs().add(d, 'day').format('YYYY-MM-DD')}
              onPress={() => setQuickDate(d)}
              light
            />
          ))}
        </View>
      </View> : null}

      <View style={styles.twoColumn}>
        <View style={styles.flex}>
          <Controller control={control} name="availableFrom" render={({ field: { onChange, onBlur, value }, fieldState }) => (
            <AgInput label={t('produce.availableFrom')} placeholder="YYYY-MM-DD" value={value} onChangeText={onChange} onBlur={onBlur} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} />
          )} />
        </View>
        <View style={styles.flex}>
          <Controller control={control} name="availableUntil" render={({ field: { onChange, onBlur, value }, fieldState }) => (
            <AgInput label={t('produce.availableUntil')} placeholder="YYYY-MM-DD" value={value} onChangeText={onChange} onBlur={onBlur} error={fieldState.error ? t(fieldState.error.message ?? '') : undefined} />
          )} />
        </View>
      </View>

      <Controller
        control={control}
        name="expectedGrade"
        render={({ field: { onChange, value } }) => (
          <AgDropdown
            label={t('produce.expectedGrade')}
            title={t('produce.expectedGrade')}
            placeholder={t('produce.selectGrade')}
            value={value}
            options={gradeOptions}
            onChange={onChange}
          />
        )}
      />

      <Controller control={control} name="packaging" render={({ field: { onChange, onBlur, value } }) => (
        <AgInput label={t('produce.packaging')} placeholder={t('produce.packagingPlaceholder')} value={value} onChangeText={onChange} onBlur={onBlur} />
      )} />

      <Controller
        control={control}
        name="askingPrice"
        render={({ field: { onChange, onBlur, value }, fieldState }) => (
          <AgInput
            label={t('produce.askingPrice')}
            hint={t('produce.askingPriceHint')}
            placeholder="0"
            keyboardType="numeric"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
      />

      <Controller control={control} name="priceUnit" render={({ field: { onChange, value } }) => (
        <AgDropdown label={t('produce.priceUnit')} title={t('produce.priceUnit')} placeholder={t('produce.priceUnit')} value={value} options={unitOptions} onChange={onChange} />
      )} />

      <Controller control={control} name="negotiable" render={({ field: { onChange, value } }) => (
        <View style={styles.switchRow}>
          <AgText weight="semibold" style={styles.ink}>{t('produce.negotiable')}</AgText>
          <Switch value={value} onValueChange={onChange} accessibilityLabel={t('produce.negotiable')} trackColor={{ false: C.border, true: C.green }} thumbColor={C.paper} />
        </View>
      )} />

      <Controller control={control} name="pickupLocation" render={({ field: { onChange, onBlur, value } }) => (
        <AgInput label={t('produce.pickupLocation')} placeholder={t('produce.pickupLocationPlaceholder')} value={value} onChangeText={onChange} onBlur={onBlur} />
      )} />

      {mode === 'edit' ? (
        <Controller
          control={control}
          name="status"
          render={({ field: { onChange, value } }) => (
            <AgDropdown
              label={t('produce.status')}
              title={t('produce.status')}
              placeholder={t('produce.status')}
              value={value}
              options={statusOptions}
              onChange={onChange}
            />
          )}
        />
      ) : null}

      <Controller
        control={control}
        name="qualityNotes"
        render={({ field: { onChange, onBlur, value }, fieldState }) => (
          <AgInput
            label={t('produce.qualityNotes')}
            placeholder={t('produce.qualityNotesPlaceholder')}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            multiline
            numberOfLines={3}
            error={fieldState.error ? t(fieldState.error.message ?? '') : undefined}
          />
        )}
      />

      <Controller
        control={control}
        name="notes"
        render={({ field: { onChange, onBlur, value } }) => (
          <AgInput
            label={t('produce.notes')}
            placeholder={t('produce.notesPlaceholder')}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            multiline
            numberOfLines={3}
          />
        )}
      />

      {showPhotos ? (
        <View style={styles.photoSection}>
          <AgText variant="label" weight="semibold" color="muted" style={styles.sectionLabel}>
            {t('produce.photos')}
          </AgText>
          <View style={styles.photoRow}>
            {images.map((img, index) => (
              <View key={img.imageUrl} style={styles.photoWrap}>
                <Image
                  source={{ uri: img.imageUrl }}
                  style={{ width: 72, height: 72, borderRadius: 12 }}
                  contentFit="cover"
                />
                <TouchableOpacity
                  activeOpacity={0.75}
                  onPress={() => setImages((p) => p.filter((_, i) => i !== index))}
                  accessibilityRole="button"
                  accessibilityLabel={t('produce.removePhoto')}
                  style={styles.removePhoto}
                >
                  <X size={14} color={C.paper} />
                </TouchableOpacity>
              </View>
            ))}
            <TouchableOpacity
              activeOpacity={0.75}
              onPress={addPhoto}
              disabled={uploading}
              accessibilityRole="button"
              accessibilityLabel={t('produce.addPhoto')}
              style={styles.addPhoto}
            >
              {uploading ? (
                <Plus size={22} color={C.muted} />
              ) : (
                <Camera size={22} color={C.green} />
              )}
            </TouchableOpacity>
          </View>
        </View>
      ) : null}

      {errorKey ? (
        <AgText variant="bodySmall" color="danger" style={styles.errorText}>
          {t(errorKey)}
        </AgText>
      ) : null}

      <AgButton
        title={mode === 'create' ? t('produce.submit') : t('produce.saveChanges')}
        onPress={submit}
        loading={submitting}
        fullWidth
        light
        size="lg"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  form: {
    width: '100%',
    maxWidth: 768,
    alignSelf: 'center',
    gap: 18,
    paddingBottom: 24,
  },
  availabilityCard: {
    gap: 10,
    padding: 16,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
  },
  sectionLabel: { color: C.ink },
  segmentRow: { flexDirection: 'row', gap: 10 },
  segment: {
    minHeight: 56,
    flex: 1,
    paddingHorizontal: 12,
    borderRadius: 16,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  segmentSelected: { backgroundColor: C.green, borderColor: C.green },
  segmentIdle: { backgroundColor: C.paper, borderColor: C.border },
  twoColumn: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  flex: { flex: 1, minWidth: 0 },
  quickDates: { marginTop: 10, flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  switchRow: {
    minHeight: 64,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: C.border,
    backgroundColor: C.paper,
  },
  ink: { color: C.ink },
  muted: { color: C.muted },
  errorText: { color: C.danger },
  noFarmCard: {
    marginTop: 16, gap: 10, padding: 20, borderRadius: 20,
    borderWidth: 1, borderColor: C.border, backgroundColor: C.paper,
  },
  photoSection: { gap: 10 },
  photoRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  photoWrap: { position: 'relative' },
  removePhoto: {
    position: 'absolute', right: -4, top: -4, width: 28, height: 28,
    borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: C.danger,
  },
  addPhoto: {
    width: 80, height: 80, alignItems: 'center', justifyContent: 'center',
    borderRadius: 16, borderWidth: 1.5, borderStyle: 'dashed', borderColor: C.green,
    backgroundColor: C.greenSoft,
  },
});
