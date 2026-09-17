import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Camera,
  Check,
  GraduationCap,
  Languages,
  LocateFixed,
  MapPinned,
  Sprout,
  UserRound,
  type LucideIcon,
} from "lucide-react-native";
import { type ReactNode, useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from "react-native";

import {
  AgAvatar,
  AgDistrictDropdown,
  AgInput,
  AgScreen,
  AgText,
} from "@/components/ui";
import { DISEASE_DETECTION_CROPS } from "@/constants/crops";
import { autofillAddressFromGPS } from "@/features/auth/hooks/useLocationAutofill";
import {
  profileSchema,
  type ProfileData,
  type ProfileForm,
} from "@/features/auth/schemas";
import { useLanguage } from "@/hooks/useLanguage";
import { pickProfileImage } from "@/utils/image";

import {
  EDUCATION_SELECT_OPTIONS,
  GENDER_SELECT_OPTIONS,
  LANGUAGE_OPTIONS,
} from "../constants";
import { useProfile, useUpdateProfile } from "../hooks/useProfile";
import { useUploadAvatar } from "../hooks/useUploadAvatar";
import type { FarmerProfileInput } from "../types";

const PAGE_BG = "#FBF7EA";
const CARD_BG = "#FFFDF8";
const FIELD_BG = "#FFFFFF";
const PRIMARY_TEXT = "#173B2B";
const SECONDARY_TEXT = "#58685F";
const GREEN = "#176B3A";
const LEAF_GREEN = "#4E9B45";
const PALE_GREEN = "#EEF6EC";
const BORDER = "#D8D7C9";

function FormSection({
  icon: Icon,
  title,
  subtitle,
  children,
}: {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <View style={styles.sectionIcon}>
          <Icon size={24} color={GREEN} strokeWidth={2.1} />
        </View>
        <View style={styles.flexOne}>
          <AgText variant="headingS" weight="bold" style={styles.primaryText}>
            {title}
          </AgText>
          {subtitle ? (
            <AgText variant="bodySmall" style={styles.sectionSubtitle}>
              {subtitle}
            </AgText>
          ) : null}
        </View>
      </View>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );
}

function ChoiceChip({
  label,
  selected,
  onPress,
  icon: Icon,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  icon: LucideIcon;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.72}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={label}
      style={[styles.choiceChip, selected && styles.choiceChipSelected]}
    >
      {selected ? (
        <View style={styles.choiceCheck}>
          <Check size={13} color="#FFFFFF" strokeWidth={3} />
        </View>
      ) : (
        <Icon size={17} color={GREEN} />
      )}
      <AgText
        variant="bodySmall"
        weight={selected ? "semibold" : "medium"}
        style={styles.choiceText}
      >
        {label}
      </AgText>
    </TouchableOpacity>
  );
}

export function EditProfileScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { language } = useLanguage();
  const { width } = useWindowDimensions();
  const { data: profile } = useProfile();
  const save = useUpdateProfile();
  const upload = useUploadAvatar();
  const [locating, setLocating] = useState(false);
  const compact = width < 360;

  const { control, handleSubmit, watch, setValue, reset, formState } = useForm<
    ProfileForm,
    unknown,
    ProfileData
  >({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: profile?.fullName ?? "",
      language: profile?.language ?? language,
      district: profile?.district ?? "",
      block: profile?.block ?? "",
      village: profile?.village ?? "",
      experienceYears:
        profile?.experienceYears != null ? String(profile.experienceYears) : "",
      gender: profile?.gender ?? null,
      education: profile?.education ?? null,
      preferredCrops: profile?.preferredCrops ?? [],
      photoUrl: profile?.photoUrl ?? null,
    },
    mode: "onChange",
  });

  useEffect(() => {
    if (!profile) return;
    reset({
      name: profile.fullName,
      language: profile.language,
      district: profile.district ?? "",
      block: profile.block ?? "",
      village: profile.village ?? "",
      experienceYears:
        profile.experienceYears != null ? String(profile.experienceYears) : "",
      gender: profile.gender,
      education: profile.education,
      preferredCrops: profile.preferredCrops,
      photoUrl: profile.photoUrl,
    });
  }, [profile, reset]);

  const photoUrl = watch("photoUrl");
  const selectedLanguage = watch("language");
  const selectedGender = watch("gender");
  const selectedEducation = watch("education");
  const name = watch("name");
  const selectedCrops = watch("preferredCrops") ?? [];

  const onPickPhoto = async () => {
    const uri = await pickProfileImage();
    if (!uri) return;
    try {
      const url = await upload.mutateAsync(uri);
      setValue("photoUrl", url, { shouldValidate: true });
    } catch {
      Alert.alert(t("profile.uploadFailed"));
    }
  };

  const toggleCrop = (id: string) => {
    const next = new Set(selectedCrops);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setValue("preferredCrops", Array.from(next), { shouldValidate: true });
  };

  const onSubmit = handleSubmit((data) => {
    const input: FarmerProfileInput = {
      fullName: data.name,
      language: data.language,
      district: data.district || null,
      block: data.block || null,
      village: data.village || null,
      experienceYears: data.experienceYears,
      gender: data.gender,
      education: data.education,
      preferredCrops: data.preferredCrops,
      photoUrl: data.photoUrl,
    };
    save.mutate(input, {
      onSuccess: ({ offline }) => {
        Alert.alert(offline ? t("profile.savedOffline") : t("profile.saved"));
        router.back();
      },
      onError: () => Alert.alert(t("profile.saveFailed")),
    });
  });

  const onUseMyLocation = async () => {
    setLocating(true);
    try {
      const result = await autofillAddressFromGPS();
      if (result.status === "permissionDenied") {
        Alert.alert(t("profile.locationPermissionDenied"));
        return;
      }
      if (result.status === "unavailable") {
        Alert.alert(t("profile.locationUnavailable"));
        return;
      }
      if (result.status === "noDistrictMatch") {
        Alert.alert(t("profile.locationDistrictNotFound"));
        return;
      }
      if (result.district)
        setValue("district", result.district, { shouldValidate: true });
      if (result.block) setValue("block", result.block);
      if (result.village) setValue("village", result.village);
    } finally {
      setLocating(false);
    }
  };

  const fieldTheme = {
    fieldStyle: styles.field,
    fieldBorderColor: BORDER,
    fieldBackgroundColor: FIELD_BG,
    focusBorderColor: GREEN,
    labelStyle: styles.fieldLabel,
    style: styles.inputText,
    placeholderTextColor: SECONDARY_TEXT,
  };

  return (
    <AgScreen
      scroll
      keyboardAvoiding
      backgroundColor={PAGE_BG}
      contentContainerStyle={styles.screenContent}
    >
      <View style={styles.pageHeader}>
        <TouchableOpacity
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          activeOpacity={0.72}
          style={styles.backButton}
        >
          <ArrowLeft size={24} color={PRIMARY_TEXT} />
        </TouchableOpacity>
        <View style={styles.headerCopy}>
          <AgText variant="headingL" weight="bold" style={styles.primaryText}>
            {t("profile.editTitle")}
          </AgText>
          <AgText variant="body" style={styles.headerSubtitle}>
            {t("profile.editSubtitle")}
          </AgText>
        </View>
      </View>

      <View
        style={[styles.identityCard, compact && styles.identityCardCompact]}
      >
        <View style={styles.avatarWrap}>
          <AgAvatar uri={photoUrl} name={name} size={92} light />
          {upload.isPending ? (
            <View style={styles.avatarLoading}>
              <ActivityIndicator color="#FFFFFF" />
            </View>
          ) : null}
          <View style={styles.cameraBadge}>
            <Camera size={17} color="#FFFFFF" />
          </View>
        </View>
        <View style={styles.identityCopy}>
          <AgText
            variant="headingS"
            weight="bold"
            style={styles.primaryText}
            numberOfLines={2}
          >
            {name || t("profile.namePlaceholderRedesign")}
          </AgText>
          <AgText variant="bodySmall" style={styles.identityHint}>
            {t("profile.editSubtitle")}
          </AgText>
          <TouchableOpacity
            onPress={onPickPhoto}
            disabled={upload.isPending}
            activeOpacity={0.72}
            accessibilityRole="button"
            accessibilityLabel={t("profile.changePhoto")}
            style={styles.photoButton}
          >
            <Camera size={17} color={GREEN} />
            <AgText
              variant="bodySmall"
              weight="semibold"
              style={styles.greenText}
            >
              {upload.isPending
                ? t("profile.uploading")
                : photoUrl
                  ? t("profile.changePhoto")
                  : t("profile.addPhoto")}
            </AgText>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.sections}>
        <FormSection icon={UserRound} title={t("profile.aboutYou")}>
          <Controller
            control={control}
            name="name"
            render={({ field: { onChange, onBlur, value }, fieldState }) => (
              <AgInput
                {...fieldTheme}
                label={t("profile.name")}
                required
                placeholder={t("profile.namePlaceholderRedesign")}
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                autoCapitalize="words"
                error={
                  fieldState.error
                    ? t(fieldState.error.message ?? "")
                    : undefined
                }
                leftAccessory={<UserRound size={20} color={GREEN} />}
              />
            )}
          />
          <View>
            <View style={styles.controlLabel}>
              <Languages size={18} color={GREEN} />
              <AgText
                variant="label"
                weight="semibold"
                style={styles.primaryText}
              >
                {t("profile.language")}
              </AgText>
            </View>
            <View style={styles.choiceRow}>
              {LANGUAGE_OPTIONS.map((option) => (
                <ChoiceChip
                  key={option.value}
                  label={option.label}
                  selected={selectedLanguage === option.value}
                  onPress={() =>
                    setValue("language", option.value, { shouldValidate: true })
                  }
                  icon={Languages}
                />
              ))}
            </View>
          </View>
        </FormSection>

        <FormSection
          icon={MapPinned}
          title={t("profile.farmLocation")}
          subtitle={t("profile.locationSubtitle")}
        >
          <View style={styles.locationCard}>
            <View style={styles.locationIcon}>
              <LocateFixed size={23} color={GREEN} />
            </View>
            <View style={styles.locationCopy}>
              <AgText
                variant="body"
                weight="semibold"
                style={styles.primaryText}
              >
                {t("profile.useMyLocation")}
              </AgText>
              <AgText variant="bodySmall" style={styles.locationHint}>
                {t("profile.locationAutofillSubtitle")}
              </AgText>
            </View>
            <TouchableOpacity
              onPress={onUseMyLocation}
              disabled={locating}
              activeOpacity={0.72}
              accessibilityRole="button"
              accessibilityLabel={t("profile.useLocationAction")}
              style={[
                styles.locationButton,
                compact && styles.locationButtonCompact,
              ]}
            >
              {locating ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <LocateFixed size={17} color="#FFFFFF" />
              )}
              <AgText
                variant="bodySmall"
                weight="semibold"
                style={styles.buttonText}
              >
                {t("profile.useLocationAction")}
              </AgText>
            </TouchableOpacity>
          </View>
          <Controller
            control={control}
            name="district"
            render={({ field: { onChange, value }, fieldState }) => (
              <AgDistrictDropdown
                label={t("profile.district")}
                placeholder={t("profile.selectDistrict")}
                value={value}
                onChange={(districtId) => {
                  if (districtId !== value) {
                    setValue("block", "", { shouldDirty: true });
                    setValue("village", "", { shouldDirty: true });
                  }
                  onChange(districtId);
                }}
                error={
                  fieldState.error
                    ? t(fieldState.error.message ?? "")
                    : undefined
                }
                leftAccessory={<MapPinned size={20} color={GREEN} />}
                fieldStyle={styles.field}
                textStyle={styles.dropdownText}
                labelStyle={styles.fieldLabel}
              />
            )}
          />
          <View style={[styles.twoColumnRow, compact && styles.stackedRow]}>
            <View style={styles.flexOne}>
              <Controller
                control={control}
                name="block"
                render={({ field: { onChange, onBlur, value } }) => (
                  <AgInput
                    {...fieldTheme}
                    label={t("profile.block")}
                    placeholder={t("profile.blockPlaceholder")}
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                  />
                )}
              />
            </View>
            <View style={styles.flexOne}>
              <Controller
                control={control}
                name="village"
                render={({ field: { onChange, onBlur, value } }) => (
                  <AgInput
                    {...fieldTheme}
                    label={t("profile.village")}
                    placeholder={t("profile.villagePlaceholder")}
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                  />
                )}
              />
            </View>
          </View>
        </FormSection>

        <FormSection icon={Sprout} title={t("profile.yourFarming")}>
          <Controller
            control={control}
            name="experienceYears"
            render={({ field: { onChange, onBlur, value }, fieldState }) => (
              <AgInput
                {...fieldTheme}
                label={t("profile.experience")}
                placeholder={t("profile.experiencePlaceholder")}
                keyboardType="number-pad"
                maxLength={2}
                value={value ?? ""}
                onChangeText={onChange}
                onBlur={onBlur}
                error={
                  fieldState.error
                    ? t(fieldState.error.message ?? "")
                    : undefined
                }
                leftAccessory={<Sprout size={20} color={GREEN} />}
              />
            )}
          />
          <View>
            <AgText
              variant="label"
              weight="semibold"
              style={styles.controlHeading}
            >
              {t("profile.gender")}
            </AgText>
            <View style={styles.choiceRow}>
              {GENDER_SELECT_OPTIONS.map((option) => (
                <ChoiceChip
                  key={option.value}
                  label={t(option.labelKey)}
                  selected={selectedGender === option.value}
                  onPress={() =>
                    setValue(
                      "gender",
                      selectedGender === option.value ? null : option.value,
                      { shouldValidate: true },
                    )
                  }
                  icon={UserRound}
                />
              ))}
            </View>
          </View>
          <View>
            <View style={styles.controlLabel}>
              <GraduationCap size={18} color={GREEN} />
              <AgText
                variant="label"
                weight="semibold"
                style={styles.primaryText}
              >
                {t("profile.education")}
              </AgText>
            </View>
            <View style={styles.choiceRow}>
              {EDUCATION_SELECT_OPTIONS.map((option) => (
                <ChoiceChip
                  key={option.value}
                  label={t(option.labelKey)}
                  selected={selectedEducation === option.value}
                  onPress={() =>
                    setValue(
                      "education",
                      selectedEducation === option.value ? null : option.value,
                      { shouldValidate: true },
                    )
                  }
                  icon={GraduationCap}
                />
              ))}
            </View>
          </View>
        </FormSection>

        <FormSection
          icon={Sprout}
          title={t("profile.crops")}
          subtitle={t("profile.cropsSelectAll")}
        >
          <View style={styles.cropGrid}>
            {DISEASE_DETECTION_CROPS.map((crop) => {
              const selected = selectedCrops.includes(crop.id);
              const label = language === "ta" ? crop.ta : crop.en;
              return (
                <TouchableOpacity
                  key={crop.id}
                  onPress={() => toggleCrop(crop.id)}
                  activeOpacity={0.72}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: selected }}
                  accessibilityLabel={label}
                  style={[
                    styles.cropCard,
                    compact && styles.cropCardCompact,
                    selected && styles.cropCardSelected,
                  ]}
                >
                  <Sprout
                    size={25}
                    color={selected ? GREEN : SECONDARY_TEXT}
                    strokeWidth={1.8}
                  />
                  <AgText
                    variant="bodySmall"
                    weight={selected ? "semibold" : "medium"}
                    numberOfLines={2}
                    style={styles.cropText}
                  >
                    {label}
                  </AgText>
                  {selected ? (
                    <View style={styles.cropCheck}>
                      <Check size={13} color="#FFFFFF" strokeWidth={3} />
                    </View>
                  ) : null}
                </TouchableOpacity>
              );
            })}
          </View>
        </FormSection>
      </View>

      <TouchableOpacity
        onPress={onSubmit}
        disabled={!formState.isValid || upload.isPending || save.isPending}
        activeOpacity={0.78}
        accessibilityRole="button"
        accessibilityLabel={t("common.save")}
        style={[
          styles.saveButton,
          (!formState.isValid || upload.isPending || save.isPending) &&
            styles.buttonDisabled,
        ]}
      >
        {save.isPending ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <>
            <AgText variant="bodyLarge" weight="bold" style={styles.buttonText}>
              {t("common.save")}
            </AgText>
            <Check size={21} color="#FFFFFF" strokeWidth={2.5} />
          </>
        )}
      </TouchableOpacity>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screenContent: { paddingTop: 10, paddingBottom: 72 },
  flexOne: { flex: 1, minWidth: 0 },
  primaryText: { color: PRIMARY_TEXT },
  greenText: { color: GREEN },
  pageHeader: {
    minHeight: 64,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
  },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: CARD_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  headerCopy: { flex: 1, minWidth: 0 },
  headerSubtitle: { marginTop: 1, color: SECONDARY_TEXT },
  identityCard: {
    marginTop: 20,
    padding: 18,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "#BCD4BE",
    backgroundColor: CARD_BG,
    flexDirection: "row",
    alignItems: "center",
    gap: 18,
    shadowColor: PRIMARY_TEXT,
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  identityCardCompact: { alignItems: "flex-start" },
  avatarWrap: { width: 96, height: 96 },
  avatarLoading: {
    position: "absolute",
    inset: 0,
    width: 92,
    height: 92,
    borderRadius: 46,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(23,59,43,0.58)",
  },
  cameraBadge: {
    position: "absolute",
    right: 0,
    bottom: 1,
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 3,
    borderColor: CARD_BG,
    backgroundColor: GREEN,
    alignItems: "center",
    justifyContent: "center",
  },
  identityCopy: { flex: 1, minWidth: 0 },
  identityHint: { marginTop: 3, color: SECONDARY_TEXT },
  photoButton: {
    alignSelf: "flex-start",
    minHeight: 42,
    marginTop: 10,
    paddingHorizontal: 14,
    borderRadius: 13,
    borderWidth: 1.25,
    borderColor: GREEN,
    backgroundColor: PALE_GREEN,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },
  sections: { marginTop: 16, gap: 14 },
  sectionCard: {
    padding: 17,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E2DED1",
    backgroundColor: CARD_BG,
    shadowColor: PRIMARY_TEXT,
    shadowOpacity: 0.05,
    shadowRadius: 7,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  sectionHeader: { flexDirection: "row", alignItems: "center", gap: 12 },
  sectionIcon: {
    width: 46,
    height: 46,
    borderRadius: 15,
    backgroundColor: PALE_GREEN,
    alignItems: "center",
    justifyContent: "center",
  },
  sectionSubtitle: { marginTop: 1, color: SECONDARY_TEXT },
  sectionContent: { marginTop: 17, gap: 17 },
  field: {
    minHeight: 56,
    borderRadius: 13,
    borderWidth: 1.25,
    borderColor: BORDER,
    backgroundColor: FIELD_BG,
  },
  fieldLabel: { color: PRIMARY_TEXT },
  inputText: { color: PRIMARY_TEXT, backgroundColor: "transparent" },
  dropdownText: { color: PRIMARY_TEXT },
  controlLabel: {
    marginBottom: 9,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  controlHeading: { marginBottom: 9, color: PRIMARY_TEXT },
  choiceRow: { flexDirection: "row", flexWrap: "wrap", gap: 9 },
  choiceChip: {
    minHeight: 44,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1.25,
    borderColor: BORDER,
    backgroundColor: FIELD_BG,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },
  choiceChipSelected: { borderColor: LEAF_GREEN, backgroundColor: PALE_GREEN },
  choiceText: { color: PRIMARY_TEXT },
  choiceCheck: {
    width: 19,
    height: 19,
    borderRadius: 10,
    backgroundColor: GREEN,
    alignItems: "center",
    justifyContent: "center",
  },
  locationCard: {
    padding: 14,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: "#BFD2BF",
    backgroundColor: PALE_GREEN,
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    flexWrap: "wrap",
  },
  locationIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#C9D9C8",
    backgroundColor: CARD_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  locationCopy: { flex: 1, minWidth: 150 },
  locationHint: { color: SECONDARY_TEXT, lineHeight: 19 },
  locationButton: {
    minHeight: 44,
    paddingHorizontal: 14,
    borderRadius: 13,
    backgroundColor: GREEN,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },
  locationButtonCompact: { width: "100%" },
  twoColumnRow: { flexDirection: "row", gap: 12 },
  stackedRow: { flexDirection: "column" },
  cropGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  cropCard: {
    width: "31%",
    minHeight: 88,
    paddingHorizontal: 8,
    paddingVertical: 12,
    borderRadius: 14,
    borderWidth: 1.25,
    borderColor: BORDER,
    backgroundColor: FIELD_BG,
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  cropCardCompact: { width: "48%" },
  cropCardSelected: { borderColor: LEAF_GREEN, backgroundColor: PALE_GREEN },
  cropText: { color: PRIMARY_TEXT, textAlign: "center", lineHeight: 19 },
  cropCheck: {
    position: "absolute",
    right: 7,
    top: 7,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: GREEN,
    alignItems: "center",
    justifyContent: "center",
  },
  saveButton: {
    minHeight: 58,
    marginTop: 18,
    paddingHorizontal: 24,
    borderRadius: 16,
    backgroundColor: GREEN,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 11,
  },
  buttonText: { color: "#FFFFFF" },
  buttonDisabled: { opacity: 0.45 },
});
