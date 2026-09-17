import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  CalendarDays,
  Camera,
  ChevronRight,
  CirclePlus,
  Droplets,
  FileText,
  Home,
  LandPlot,
  Leaf,
  LocateFixed,
  MapPin,
  Sprout,
  Waves,
} from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Alert, Pressable as AgPressable, StyleSheet, View } from "react-native";

import {
  AgButton,
  AgCard,
  AgChip,
  AgCropDropdown,
  AgDatePicker,
  AgDistrictDropdown,
  AgWaterSourceDropdown,
  AgInput,
  AgIrrigationTypeDropdown,
  AgScreen,
  AgSoilTypeDropdown,
  AgText,
} from "@/components/ui";
import { COMMON_CROPS } from "@/constants/crops";
import { autofillAddressFromCoordinates } from "@/features/auth/hooks/useLocationAutofill";
import { captureFromCamera } from "@/features/disease/utils/pickDiseaseImage";
import { identifyPlant } from "@/features/plantIdentifier/plantIdentifierApi";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";
import { ApiError } from "@/types";

import { BoundaryEditor } from "../components/BoundaryEditor";
import {
  AREA_SOURCES,
  FARM_STATUSES,
  IRRIGATION_TYPES,
  SOIL_TYPES,
  WATER_SOURCES,
} from "../constants";
import { useCurrentLocation } from "../hooks/useCurrentLocation";
import { useFarm } from "../hooks/useFarms";
import { useCreateFarm, useUpdateFarm } from "../hooks/useFarmMutations";
import {
  farmFormSchema,
  type FarmFormData,
  type FarmFormInput,
} from "../schemas";
import { FarmError } from "../services/farmProvider";
import type {
  BoundaryInput,
  FarmInput,
  FarmLocation,
  FarmStatus,
  LatLng,
} from "../types";
import { centroid, ringToPolygon, validateRing } from "../utils/geo";
import { matchCropId } from "../utils/cropMatch";

const SCREEN_BG = '#F7F3E8';
const SURFACE = '#FFFFFF';
const SURFACE_ACCENT = "#EAF3E5";
const BORDER = "#D9D6C8";
const TEXT = "#101713";
const MUTED = "#536158";
const GREEN = "#176B36";
const NOTES_MAX_LENGTH = 2000;

function farmErrorKey(error: unknown): string {
  if (error instanceof FarmError) return error.message;
  if (error instanceof ApiError) {
    if (error.errorCode === "duplicate_farm") return "farm.errorDuplicate";
    if (error.isNetwork) return "common.offlineMessage";
  }
  return "errors.generic";
}

export function FarmFormScreen({ farmId }: { farmId?: string }) {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language, isTamil } = useLanguage();
  const soilOptions = SOIL_TYPES.map((option) => {
    const english = i18n.getFixedT("en")(option.labelKey);
    const tamil = i18n.getFixedT("ta")(option.labelKey);
    return {
      value: option.value,
      label: language === "ta" ? tamil : english,
      alternateLabel: language === "ta" ? english : tamil,
    };
  });
  const irrigationOptions = IRRIGATION_TYPES.map((option) => {
    const english = i18n.getFixedT("en")(option.labelKey);
    const tamil = i18n.getFixedT("ta")(option.labelKey);
    return {
      value: option.value,
      label: language === "ta" ? tamil : english,
      alternateLabel: language === "ta" ? english : tamil,
      subtitle: t(`irrigationSelector.descriptions.${option.value}`),
    };
  });
  const waterSourceOptions = WATER_SOURCES.map((option) => {
    const english = i18n.getFixedT("en")(option.labelKey);
    const tamil = i18n.getFixedT("ta")(option.labelKey);
    return {
      value: option.value,
      label: language === "ta" ? tamil : english,
      alternateLabel: language === "ta" ? english : tamil,
    };
  });
  const isEdit = Boolean(farmId);

  const farmQuery = useFarm(farmId);
  const { data: farm } = farmQuery;
  const create = useCreateFarm();
  const update = useUpdateFarm(farmId ?? "");
  const {
    getCurrentLocation,
    loading: locating,
    error: locationError,
  } = useCurrentLocation();

  const [vertices, setVertices] = useState<LatLng[]>([]);
  const [gps, setGps] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number | null;
  } | null>(null);
  const [mapCenter, setMapCenter] = useState<LatLng | null>(null);
  const [cropSuggestion, setCropSuggestion] = useState<{
    matchedId: string;
    label: string;
  } | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [addressLoading, setAddressLoading] = useState(false);
  const cropLock = useRef(false);
  const gpsLock = useRef(false);
  const saveLock = useRef(false);
  const seededFarm = useRef<string | undefined>(undefined);

  const { control, handleSubmit, watch, getValues, setValue, reset, formState } =
    useForm<FarmFormInput, unknown, FarmFormData>({
    resolver: zodResolver(farmFormSchema),
    defaultValues: {
      name: "",
      crop: "",
      cropVariety: "",
      sowingDate: "",
      soilType: "",
      irrigationType: "",
      waterSource: "",
      district: "",
      block: "",
      village: "",
      status: "active",
      notes: "",
      areaSource: "auto",
      areaManual: "",
    },
    mode: "onChange",
  });

  // Seed the form when editing an existing farm.
  useEffect(() => {
    if (!farm || seededFarm.current === farm.id) return;
    seededFarm.current = farm.id;
    reset({
      name: farm.name,
      crop: farm.crop ?? "",
      cropVariety: farm.cropVariety ?? "",
      sowingDate: farm.sowingDate ?? "",
      soilType: farm.soilType ?? "",
      irrigationType: farm.irrigationType ?? "",
      waterSource: farm.waterSource ?? "",
      district: farm.location?.district ?? "",
      block: farm.location?.block ?? "",
      village: farm.location?.village ?? "",
      status: farm.status,
      notes: farm.notes ?? "",
      areaSource: farm.areaSource,
      areaManual:
        farm.areaSource === "manual" && farm.areaHectares != null
          ? String(farm.areaHectares)
          : "",
    });
    setVertices(
      farm.boundary?.geojson
        ? farm.boundary.geojson.coordinates[0]
            .slice(0, -1)
            .map(([lng, lat]) => ({ latitude: lat, longitude: lng }))
        : [],
    );
    if (farm.location?.latitude != null && farm.location?.longitude != null) {
      setGps({
        latitude: farm.location.latitude,
        longitude: farm.location.longitude,
        accuracy: farm.location.accuracy,
      });
    }
  }, [farm, reset]);

  const areaSource = watch("areaSource");

  const detectGps = async () => {
    if (gpsLock.current || saveLock.current) return;
    gpsLock.current = true;
    setAddressLoading(true);
    let addressTimeout: ReturnType<typeof setTimeout> | undefined;
    try {
    const loc = await getCurrentLocation();
    if (loc) {
      setGps(loc);
      setMapCenter({ latitude: loc.latitude, longitude: loc.longitude });

      const address = await Promise.race([
        autofillAddressFromCoordinates(loc.latitude, loc.longitude),
        new Promise<never>((_, reject) => {
          addressTimeout = setTimeout(() => reject(new Error("ADDRESS_TIMEOUT")), 12000);
        }),
      ]);
      if (address.district) {
        setValue('district', address.district, {
          shouldDirty: true,
          shouldValidate: true,
        });
      }
      if (address.block) {
        setValue('block', address.block, {
          shouldDirty: true,
          shouldValidate: true,
        });
      }
      if (address.village) {
        setValue('village', address.village, {
          shouldDirty: true,
          shouldValidate: true,
        });
      }

      const hasCompleteAddress = Boolean(address.district && address.block && address.village);
      if (!hasCompleteAddress) {
        Alert.alert(
          t("farm.locationAddressPartialTitle"),
          t(
            address.status === "unavailable"
              ? 'farm.locationAddressUnavailable'
              : 'farm.locationAddressPartial',
          ),
        );
      }
    }
    } catch {
      Alert.alert(t("farm.locationAddressPartialTitle"), t("farm.locationAddressUnavailable"));
    } finally {
      if (addressTimeout) clearTimeout(addressTimeout);
      gpsLock.current = false;
      setAddressLoading(false);
    }
  };

  const detectCrop = async () => {
    if (cropLock.current || saveLock.current) return;
    cropLock.current = true;
    setDetecting(true);
    try {
      const image = await captureFromCamera({ base64: false });
      if (!image) return;
      setCropSuggestion(null);
      const result = await identifyPlant({
        uri: image.uri,
        mimeType: image.mimeType,
      });
      const matchedId = matchCropId(result.common_name);
      if (matchedId) {
        const crop = COMMON_CROPS.find((item) => item.id === matchedId);
        if (crop) {
          setCropSuggestion({ matchedId, label: isTamil ? crop.ta : crop.en });
        }
      } else {
        Alert.alert(t("farm.cropDetectNoMatch"));
      }
    } catch (error) {
      const message =
        error instanceof ApiError &&
        error.errorCode === "ai_daily_quota_exceeded"
          ? t("plantIdentifier.quotaExceeded")
          : t("farm.cropDetectFailed");
      Alert.alert(message);
    } finally {
      cropLock.current = false;
      setDetecting(false);
    }
  };

  const toOptions = (list: { value: string; labelKey: string }[]) =>
    list.map((o) => ({ value: o.value, label: t(o.labelKey) }));

  const buildInput = (data: FarmFormData): FarmInput | null => {
    if (data.areaSource === "manual" && data.areaManual == null) {
      Alert.alert(t("farm.errorAreaRequired"));
      return null;
    }
    if (vertices.length > 0) {
      const check = validateRing(vertices);
      if (!check.ok) {
        Alert.alert(t(check.errorKey ?? "farm.errorBoundaryPoints"));
        return null;
      }
    }
    const boundary: BoundaryInput | null =
      vertices.length >= 3
        ? { geojson: ringToPolygon(vertices), source: "drawn" }
        : null;
    const point = gps ?? mapCenter ?? (boundary ? centroid(vertices) : null);
    const hasLocation =
      point != null ||
      data.district !== "" ||
      data.block !== "" ||
      data.village !== "";
    const location: FarmLocation | null = hasLocation
      ? {
          latitude: point?.latitude ?? null,
          longitude: point?.longitude ?? null,
          accuracy: gps?.accuracy ?? null,
          elevation: null,
          address: null,
          district: data.district || null,
          block: data.block || null,
          village: data.village || null,
          source: gps ? "gps" : "manual",
        }
      : null;

    return {
      name: data.name,
      crop: data.crop || null,
      cropVariety: data.cropVariety || null,
      sowingDate: data.sowingDate || null,
      soilType: data.soilType || null,
      irrigationType: data.irrigationType || null,
      waterSource: data.waterSource || null,
      notes: data.notes || null,
      status: data.status,
      areaHectares: data.areaManual,
      areaSource: data.areaSource,
      location,
      boundary,
    };
  };

  const onSubmit = handleSubmit((data) => {
    if (saveLock.current || cropLock.current || gpsLock.current || (isEdit && (!farm || farmQuery.isError))) return;
    const input = buildInput(data);
    if (!input) return;
    saveLock.current = true;
    const onSuccess = ({ offline }: { offline: boolean }) => {
      Alert.alert(offline ? t("farm.savedOffline") : t("farm.saved"));
      router.back();
    };
    const onError = (error: unknown) => Alert.alert(t(farmErrorKey(error)));
    const onSettled = () => { saveLock.current = false; };
    if (isEdit) update.mutate(input, { onSuccess, onError, onSettled });
    else create.mutate(input, { onSuccess, onError, onSettled });
  });

  const saving = create.isPending || update.isPending;
  const selectedStatus = watch("status");
  const notesValue = watch("notes") ?? "";
  const fieldTheme = {
    fieldStyle: styles.field,
    fieldBorderColor: BORDER,
    fieldBackgroundColor: SURFACE,
    focusBorderColor: GREEN,
    style: styles.inputText,
    labelStyle: styles.fieldLabelText,
    hintStyle: styles.helperText,
  } as const;
  const requiredFieldsMessage = () => {
    const currentValues = getValues();
    const result = farmFormSchema.safeParse(currentValues);
    if (result.success) return null;

    const missing: string[] = [];
    const fieldLabels: Record<string, string> = {
      name: t("farm.name"),
      crop: t("farm.crop"),
      sowingDate: t("farm.sowingDate"),
    };
    for (const issue of result.error.issues) {
      const field = issue.path[0] as string;
      if (fieldLabels[field] && !missing.includes(fieldLabels[field])) {
        missing.push(fieldLabels[field]);
      }
    }
    return missing.length
      ? `${t("farm.missingFieldsPrefix")}${missing.join(", ")}`
      : t("farm.completeRequiredFields");
  };

  if (isEdit && (farmQuery.isLoading || farmQuery.isError || !farm)) {
    return <AgScreen backgroundColor={SCREEN_BG}>
      <AgButton title={t("common.back")} onPress={() => router.back()} />
      {farmQuery.isLoading ? <ActivityIndicator color={GREEN} /> : <>
        <AgText color="danger">{t(farmErrorKey(farmQuery.error))}</AgText>
        <AgButton title={t("common.retry")} disabled={farmQuery.isFetching} onPress={() => void farmQuery.refetch()} />
      </>}
    </AgScreen>;
  }

  return (
    <AgScreen
      testID="farm-form-screen"
      scroll
      keyboardAvoiding
      backgroundColor={SCREEN_BG}
      contentContainerStyle={styles.screenContent}
    >
      <View style={styles.header}>
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={styles.backButton}
        >
          <ArrowLeft size={24} color={TEXT} />
        </AgPressable>
        <View style={styles.headerIcon}>
          <Sprout size={25} color={GREEN} />
        </View>
        <View style={styles.headerCopy}>
          {isEdit ? (
            <AgText variant="headingM" weight="bold" style={styles.primaryText}>
              {t("farm.editTitle")}
            </AgText>
          ) : (
            <View
              style={styles.headerTitleRow}
              accessibilityLabel={t("farm.addTitle")}
            >
              <AgText
                variant="headingM"
                weight="bold"
                style={styles.primaryText}
              >
                {t("farm.addTitlePrefix")}{" "}
              </AgText>
              <AgText variant="headingM" weight="bold" style={styles.greenText}>
                {t("farm.addTitleFarm")}
              </AgText>
            </View>
          )}
          <AgText variant="bodySmall" style={styles.secondaryText}>
            {t("farm.formSubtitle")}
          </AgText>
        </View>
      </View>

      <View style={styles.form}>
        <Controller
          control={control}
          name="name"
          render={({ field: { onChange, onBlur, value }, fieldState }) => (
            <AgInput
              {...fieldTheme}
              label={t("farm.name")}
              required
              placeholder={t("farm.namePlaceholder")}
              placeholderTextColor={MUTED}
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              error={
                fieldState.error ? t(fieldState.error.message ?? "") : undefined
              }
              leftAccessory={<Home size={22} color={GREEN} />}
            />
          )}
        />

        <AgPressable
          onPress={() => void detectCrop()}
          disabled={detecting || saving}
          accessibilityRole="button"
          accessibilityLabel={t("farm.cropDetectButton")}
          accessibilityState={{ disabled: detecting, busy: detecting }}
          style={styles.detectCard}
        >
          <View style={styles.detectIcon}>
            <Camera size={24} color={GREEN} />
          </View>
          <View style={styles.detectCopy}>
            <AgText variant="body" weight="semibold" style={styles.primaryText}>
              {t("farm.cropDetectButton")}
            </AgText>
            <AgText variant="bodySmall" style={styles.secondaryText}>
              {t("farm.cropDetectSubtitle")}
            </AgText>
          </View>
          {detecting ? (
            <AgText variant="caption" style={styles.secondaryText}>
              {t("common.loading")}
            </AgText>
          ) : (
            <ChevronRight size={22} color={MUTED} />
          )}
        </AgPressable>

        {cropSuggestion ? (
          <AgCard style={styles.detectedCard}>
            <AgText variant="caption" style={styles.secondaryText}>
              {t("farm.detectedCropLabel")}
            </AgText>
            <AgText variant="bodySmall">
              {t("farm.cropDetectSuggestion", { crop: cropSuggestion.label })}
            </AgText>
            <View className="flex-row gap-2">
              <AgButton
                title={t("common.confirm")}
                size="sm"
                light
                onPress={() => {
                  setValue("crop", cropSuggestion.matchedId, {
                    shouldValidate: true,
                    shouldDirty: true,
                  });
                  setCropSuggestion(null);
                }}
              />
              <AgButton
                title={t("common.dismiss")}
                variant="ghost"
                size="sm"
                light
                onPress={() => setCropSuggestion(null)}
              />
            </View>
          </AgCard>
        ) : null}

        <Controller
          control={control}
          name="crop"
          render={({ field: { onChange, value }, fieldState }) => (
            <AgCropDropdown
              label={t("farm.crop")}
              required
              placeholder={t("farm.selectCrop")}
              value={value}
              onChange={onChange}
              error={
                fieldState.error ? t(fieldState.error.message ?? "") : undefined
              }
              leftAccessory={<Leaf size={22} color={GREEN} />}
              fieldStyle={styles.field}
              textStyle={styles.dropdownText}
              labelStyle={styles.fieldLabelText}
            />
          )}
        />

        {!cropSuggestion ? (
          <View style={styles.detectedEmpty}>
            <AgText variant="caption" style={styles.secondaryText}>
              {t("farm.detectedCropLabel")}
            </AgText>
            <AgText variant="bodySmall" style={styles.secondaryText}>
              {t("farm.noCropDetected")}
            </AgText>
          </View>
        ) : null}

        <Controller
          control={control}
          name="cropVariety"
          render={({ field: { onChange, onBlur, value } }) => (
            <AgInput
              {...fieldTheme}
              label={t("farm.variety")}
              placeholder={t("farm.varietyPlaceholder")}
              placeholderTextColor={MUTED}
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              hint={t("farm.varietyHint")}
              leftAccessory={<Sprout size={22} color={GREEN} />}
            />
          )}
        />

        {/* Boundary editor */}
        <View style={styles.sectionBlock}>
          <AgText variant="body" weight="semibold" style={styles.primaryText}>
            {t("farm.boundary")}
          </AgText>
          <AgText
            variant="bodySmall"
            style={[styles.secondaryText, styles.sectionSubtitle]}
          >
            {t("farm.boundarySubtitle")}
          </AgText>
          <BoundaryEditor
            vertices={vertices}
            onChange={setVertices}
            onCenterChange={setMapCenter}
            initialCenter={
              gps ? { latitude: gps.latitude, longitude: gps.longitude } : null
            }
          />
        </View>

        {/* Area source */}
        <View style={styles.sectionBlock}>
          <AgText variant="body" weight="semibold" style={styles.primaryText}>
            {t("farm.area")}
          </AgText>
          <View style={styles.chipRow}>
            {AREA_SOURCES.map((opt) => (
              <AgChip
                key={opt.value}
                label={t(opt.labelKey)}
                selected={areaSource === opt.value}
                onPress={() => setValue("areaSource", opt.value)}
                light
              />
            ))}
          </View>
          {areaSource === "manual" ? (
            <Controller
              control={control}
              name="areaManual"
              render={({ field: { onChange, onBlur, value }, fieldState }) => (
                <AgInput
                  {...fieldTheme}
                  containerClassName="mt-3"
                  label={t("farm.areaHectares")}
                  keyboardType="decimal-pad"
                  value={value ?? ""}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={
                    fieldState.error
                      ? t(fieldState.error.message ?? "")
                      : undefined
                  }
                />
              )}
            />
          ) : null}
        </View>

        {/* Location */}
        <View style={styles.locationCard}>
          <AgText
            variant="bodyLarge"
            weight="semibold"
            style={styles.primaryText}
          >
            {t("farm.manualLocationTitle")}
          </AgText>
          <AgText
            variant="bodySmall"
            style={[styles.secondaryText, styles.sectionSubtitle]}
          >
            {t("farm.manualLocationSubtitle")}
          </AgText>
          <AgButton
            title={gps ? t("farm.locationSet") : t("farm.useMyLocation")}
            variant="secondary"
            size="sm"
            loading={locating || addressLoading}
            disabled={locating || addressLoading || saving}
            light
            leftIcon={<LocateFixed size={18} color={colors.primary} />}
            onPress={detectGps}
          />
          {gps ? (
            <AgText variant="caption" color="muted" className="mt-2">
              {t("farm.locationCoordinates", {
                lat: gps.latitude.toFixed(5),
                lng: gps.longitude.toFixed(5),
              })}
              {gps.accuracy != null
                ? ` (${t("farm.locationAccuracy", { value: Math.round(gps.accuracy) })})`
                : ""}
            </AgText>
          ) : null}
          {locationError ? (
            <AgCard className="mt-3 gap-2 border border-warning/40 bg-warning/10">
              <AgText variant="bodySmall" color="danger">
                {locationError === "permission"
                  ? t("farm.locationPermissionDenied")
                  : t("farm.locationUnavailable")}
              </AgText>
              <AgButton
                title={t("common.retry")}
                variant="secondary"
                size="sm"
                light
                disabled={locating || addressLoading || saving}
                onPress={() => void detectGps()}
              />
            </AgCard>
          ) : null}
          <View style={styles.locationFields}>
            <Controller
              control={control}
              name="district"
              render={({ field: { onChange, value } }) => (
                <AgDistrictDropdown
                  label={t("farm.district")}
                  placeholder={t("farm.selectDistrict")}
                  value={value}
                  onChange={(districtId) => {
                    if (districtId !== value) {
                      setValue("block", "", { shouldDirty: true });
                      setValue("village", "", { shouldDirty: true });
                    }
                    onChange(districtId);
                  }}
                  leftAccessory={<MapPin size={22} color={GREEN} />}
                  fieldStyle={styles.field}
                  textStyle={styles.dropdownText}
                  labelStyle={styles.fieldLabelText}
                />
              )}
            />

            <Controller
              control={control}
              name="block"
              render={({ field: { onChange, onBlur, value } }) => (
                <AgInput
                  {...fieldTheme}
                  label={t("farm.block")}
                  placeholder={t("farm.blockPlaceholder")}
                  placeholderTextColor={MUTED}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  leftAccessory={<LandPlot size={22} color={GREEN} />}
                />
              )}
            />
            <Controller
              control={control}
              name="village"
              render={({ field: { onChange, onBlur, value } }) => (
                <AgInput
                  {...fieldTheme}
                  label={t("farm.village")}
                  placeholder={t("farm.villagePlaceholder")}
                  placeholderTextColor={MUTED}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  leftAccessory={<Home size={22} color={GREEN} />}
                />
              )}
            />
          </View>
        </View>

        <Controller
          control={control}
          name="soilType"
          render={({ field: { onChange, value } }) => (
            <AgSoilTypeDropdown
              label={t("farm.soil")}
              placeholder={t("farm.select")}
              value={value}
              options={soilOptions}
              onChange={onChange}
              leftAccessory={<LandPlot size={22} color={GREEN} />}
              fieldStyle={styles.field}
              textStyle={styles.dropdownText}
              labelStyle={styles.fieldLabelText}
            />
          )}
        />

        <Controller
          control={control}
          name="irrigationType"
          render={({ field: { onChange, value } }) => (
            <AgIrrigationTypeDropdown
              label={t("farm.irrigation")}
              placeholder={t("farm.select")}
              value={value}
              options={irrigationOptions}
              onChange={onChange}
              leftAccessory={<Droplets size={22} color={GREEN} />}
              fieldStyle={styles.field}
              textStyle={styles.dropdownText}
              labelStyle={styles.fieldLabelText}
            />
          )}
        />

        <Controller
          control={control}
          name="waterSource"
          render={({ field: { onChange, value } }) => (
            <AgWaterSourceDropdown
              label={t("farm.water")}
              placeholder={t("farm.select")}
              value={value}
              options={waterSourceOptions}
              onChange={onChange}
              leftAccessory={<Waves size={22} color={GREEN} />}
              fieldStyle={styles.field}
              textStyle={styles.dropdownText}
              labelStyle={styles.fieldLabelText}
            />
          )}
        />

        <Controller
          control={control}
          name="sowingDate"
          render={({ field: { onChange, onBlur, value }, fieldState }) => (
            <AgDatePicker
              label={t("farm.sowingDate")}
              title={t("farm.sowingDate")}
              placeholder={t("farm.selectDate")}
              value={value}
              onChange={onChange}
              onBlur={onBlur}
              error={
                fieldState.error ? t(fieldState.error.message ?? "") : undefined
              }
              leftAccessory={<CalendarDays size={22} color={GREEN} />}
              fieldStyle={styles.field}
              textStyle={styles.dropdownText}
              labelStyle={styles.fieldLabelText}
            />
          )}
        />

        <View style={styles.sectionBlock}>
          <AgText
            variant="label"
            weight="medium"
            style={[styles.primaryText, styles.fieldLabel]}
          >
            {t("farm.status")}
          </AgText>
          <View style={styles.statusRow}>
            {FARM_STATUSES.map((opt) => (
              <AgPressable
                key={opt.value}
                onPress={() =>
                  setValue("status", opt.value as FarmStatus, {
                    shouldDirty: true,
                  })
                }
                accessibilityRole="radio"
                accessibilityState={{ selected: selectedStatus === opt.value }}
                style={[
                  styles.statusPill,
                  selectedStatus === opt.value && styles.statusPillSelected,
                ]}
              >
                <View
                  pointerEvents="none"
                  style={[
                    styles.statusRadio,
                    selectedStatus === opt.value && styles.statusRadioSelected,
                  ]}
                >
                  {selectedStatus === opt.value ? (
                    <View style={styles.statusRadioDot} />
                  ) : null}
                </View>
                <AgText
                  variant="bodySmall"
                  weight="medium"
                  style={
                    selectedStatus === opt.value
                      ? styles.primaryText
                      : styles.secondaryText
                  }
                >
                  {t(opt.labelKey)}
                </AgText>
              </AgPressable>
            ))}
          </View>
        </View>

        <Controller
          control={control}
          name="notes"
          render={({ field: { onChange, onBlur, value } }) => (
            <AgInput
              {...fieldTheme}
              label={t("farm.notes")}
              placeholder={t("farm.notesPlaceholder")}
              placeholderTextColor={MUTED}
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              multiline
              numberOfLines={5}
              maxLength={NOTES_MAX_LENGTH}
              leftAccessory={<FileText size={22} color={GREEN} />}
              hint={`${notesValue.length}/${NOTES_MAX_LENGTH}`}
            />
          )}
        />
      </View>

      <AgButton
        title={isEdit ? t("common.save") : t("farm.addFarm")}
        onPress={onSubmit}
        loading={saving}
        disabled={!formState.isValid || saving || detecting || addressLoading}
        size="lg"
        light
        className="mt-8"
        leftIcon={<CirclePlus size={20} color={colors.onPrimary} />}
      />
      {!formState.isValid ? (
        <AgText
          variant="caption"
          color="danger"
          className="mt-2"
          center
          style={styles.validationText}
        >
          {requiredFieldsMessage()}
        </AgText>
      ) : null}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screenContent: { paddingHorizontal: 20, paddingTop: 18, paddingBottom: 40 },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 14,
    marginBottom: 28,
  },
  backButton: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: -8,
  },
  headerIcon: {
    width: 54,
    height: 54,
    borderRadius: 27,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: SURFACE_ACCENT,
    borderWidth: 1,
    borderColor: "#BDD2B8",
  },
  headerCopy: { flex: 1, gap: 5 },
  headerTitleRow: { flexDirection: "row", flexWrap: "wrap" },
  primaryText: { color: TEXT },
  greenText: { color: GREEN },
  secondaryText: { color: MUTED },
  form: { gap: 22 },
  field: {
    minHeight: 62,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: SURFACE,
  },
  inputText: { color: TEXT, backgroundColor: "transparent" },
  dropdownText: { color: TEXT },
  fieldLabelText: { color: '#344A3D' },
  helperText: { color: MUTED },
  validationText: { color: '#C53D36' },
  detectCard: {
    minHeight: 112,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#BDD2B8",
    backgroundColor: SURFACE,
  },
  detectIcon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: SURFACE_ACCENT,
  },
  detectCopy: { flex: 1, gap: 4 },
  detectedCard: {
    gap: 10,
    backgroundColor: SURFACE_ACCENT,
    borderColor: "#BDD2B8",
  },
  detectedEmpty: {
    gap: 5,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: "#BDD2B8",
    backgroundColor: SURFACE_ACCENT,
  },
  pressed: { opacity: 0.78 },
  sectionBlock: { gap: 10 },
  sectionSubtitle: { marginTop: -5 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  locationCard: {
    gap: 12,
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: SURFACE,
  },
  locationFields: { gap: 18, marginTop: 4 },
  fieldLabel: { marginBottom: 2 },
  statusRow: { flexDirection: "row", flexWrap: "wrap", gap: 9 },
  statusPill: {
    minWidth: 102,
    minHeight: 48,
    flexGrow: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    paddingHorizontal: 16,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: SURFACE,
  },
  statusPillSelected: { borderColor: GREEN, backgroundColor: SURFACE_ACCENT },
  statusRadio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: "#869189",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: SURFACE,
  },
  statusRadioSelected: { borderColor: GREEN },
  statusRadioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: GREEN,
  },
});
