import { zodResolver } from "@hookform/resolvers/zod";
import { Image } from "expo-image";
import { StatusBar } from "expo-status-bar";
import {
  ArrowRight,
  CalendarDays,
  Check,
  Cloud,
  Home,
  Leaf,
  LocateFixed,
  Map,
  MapPinned,
  Sprout,
  type LucideIcon,
  UserRound,
  Wheat,
} from "lucide-react-native";
import { useRef, useState, type ReactNode } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";

import {
  AgDistrictDropdown,
  AgInput,
  AgPressable,
  AgScreen,
  AgText,
} from "@/components/ui";
import { DISEASE_DETECTION_CROPS } from "@/constants/crops";
import { useLanguage } from "@/hooks/useLanguage";

import { useCompleteProfile } from "../hooks/useAuthActions";
import { autofillAddressFromGPS } from "../hooks/useLocationAutofill";
import {
  completeProfileSchema,
  type CompleteProfileData,
  type CompleteProfileForm,
} from "../schemas";

const SCREEN_BG = "#F7F4E8";
const CARD_BG = "#FFFDF8";
const FIELD_BG = "#FFFFFF";
const BORDER = "#D8D5C9";
const TEXT = "#173B2B";
const MUTED = "#58685F";
const GREEN = "#165B33";
const LEAF_GREEN = "#4E9B45";
const GOLD = "#F5B51B";

const CROP_ICONS: Record<string, LucideIcon> = {
  banana: Leaf,
  paddy: Wheat,
  cotton: Cloud,
  groundnut: Sprout,
  chilli: Leaf,
  redgram: Sprout,
};

export function CompleteProfileScreen() {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { width } = useWindowDimensions();
  const complete = useCompleteProfile();
  const [locating, setLocating] = useState(false);
  const [districtPickerRequest, setDistrictPickerRequest] = useState(0);
  const villageRef = useRef<TextInput>(null);
  const experienceRef = useRef<TextInput>(null);
  const landRef = useRef<TextInput>(null);
  const useStackedLocalityFields = width < 370;
  const useStackedFarmingFields = width < 390;
  const useTwoColumnCropGrid = width < 360;
  const useStackedLocationAction = width < 430;

  const { control, handleSubmit, watch, setValue, formState } = useForm<
    CompleteProfileForm,
    unknown,
    CompleteProfileData
  >({
    resolver: zodResolver(completeProfileSchema),
    defaultValues: {
      name: "",
      language,
      district: "",
      block: "",
      village: "",
      experienceYears: "",
      landHoldingAcres: "",
      preferredCrops: [],
      photoUrl: null,
    },
    mode: "onChange",
  });

  const selectedCrops = watch("preferredCrops") ?? [];
  const onboardingCrops = DISEASE_DETECTION_CROPS;

  const toggleCrop = (id: string) => {
    const next = new Set(selectedCrops);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setValue("preferredCrops", Array.from(next), { shouldValidate: true });
  };

  const onSubmit = handleSubmit((data) => {
    if (!complete.isPending) {
      complete.mutate(data, {
        onError: () => Alert.alert(t("profile.saveFailed")),
      });
    }
  });

  const toggleLanguage = () => {
    const nextLanguage = language === "ta" ? "en" : "ta";
    setValue("language", nextLanguage, { shouldDirty: true });
    void setLanguage(nextLanguage);
  };

  const onUseMyLocation = async () => {
    if (locating) return;
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
        Alert.alert(
          result.rawLocationHint
            ? t("profile.locationDistrictNotFoundActionable")
            : t("profile.locationDistrictNotFound"),
          undefined,
          [
            {
              text: t("common.close"),
              onPress: () => setDistrictPickerRequest((request) => request + 1),
            },
          ],
        );
        return;
      }
      if (result.district)
        setValue("district", result.district, { shouldValidate: true });
      if (result.block) setValue("block", result.block, { shouldDirty: true });
      if (result.village)
        setValue("village", result.village, { shouldDirty: true });
    } finally {
      setLocating(false);
    }
  };

  const fieldTheme = {
    fieldStyle: styles.field,
    fieldBorderColor: BORDER,
    fieldBackgroundColor: FIELD_BG,
    focusBorderColor: GREEN,
    style: styles.inputText,
  } as const;

  return (
    <AgScreen
      testID="complete-profile-screen"
      scroll
      keyboardAvoiding
      backgroundColor={SCREEN_BG}
      contentContainerStyle={styles.screen}
    >
      <StatusBar style="dark" />

      <View style={styles.topBar}>
        <View style={styles.brandRow} accessibilityLabel="AgrowAI">
          <Image
            source={require("@/assets/images/android-icon-foreground.png")}
            contentFit="contain"
            transition={0}
            style={styles.logo}
          />
          <View style={styles.wordmarkRow}>
            <AgText variant="headingS" weight="bold" style={styles.wordmark}>
              Agrow
            </AgText>
            <AgText variant="headingS" weight="bold" style={styles.wordmarkAI}>
              AI
            </AgText>
          </View>
        </View>
        <AgPressable
          onPress={toggleLanguage}
          accessibilityRole="button"
          accessibilityLabel={t("profile.changeLanguage")}
          style={({ pressed }) => [
            styles.languageButton,
            pressed && styles.pressed,
          ]}
        >
          <AgText
            variant="bodySmall"
            weight="semibold"
            style={styles.languageText}
          >
            {language === "ta" ? "English" : "தமிழ்"}
          </AgText>
        </AgPressable>
      </View>

      <View style={styles.header}>
        <AgText variant="caption" weight="bold" style={styles.eyebrow}>
          {t("profile.setupEyebrow")}
        </AgText>
        <AgText variant="headingL" weight="bold" style={styles.heading}>
          {t("profile.completeTitle")}
        </AgText>
        <AgText variant="body" style={styles.subtitle}>
          {t("profile.completeSubtitle")}
        </AgText>
      </View>

      <AgPressable
        onPress={onUseMyLocation}
        disabled={locating}
        accessibilityRole="button"
        accessibilityLabel={t("profile.useMyLocation")}
        style={({ pressed }) => [
          styles.locationCard,
          useStackedLocationAction && styles.locationCardStacked,
          pressed && styles.pressed,
        ]}
      >
        <View style={styles.locationIcon}>
          <LocateFixed size={27} color={GREEN} />
        </View>
        <View style={styles.locationCopy}>
          <AgText
            variant="bodyLarge"
            weight="semibold"
            style={styles.primaryText}
          >
            {t("profile.useMyLocation")}
          </AgText>
          <AgText variant="bodySmall" style={styles.locationSecondaryText}>
            {t("profile.locationAutofillSubtitle")}
          </AgText>
        </View>
        <View
          style={[
            styles.locationAction,
            useStackedLocationAction && styles.locationActionStacked,
          ]}
        >
          {locating ? (
            <ActivityIndicator size="small" color={TEXT} />
          ) : (
            <>
              <AgText
                variant="bodySmall"
                weight="bold"
                numberOfLines={1}
                maxFontSizeMultiplier={1.2}
                style={styles.locationActionText}
              >
                {t("profile.useLocationAction")}
              </AgText>
            </>
          )}
        </View>
      </AgPressable>

      <View style={styles.form}>
        <ProfileSection title={t("profile.aboutYou")}>
          <Controller
            control={control}
            name="name"
            render={({ field: { onChange, onBlur, value }, fieldState }) => (
              <ProfileFieldLabel label={t("profile.name")}>
                <AgInput
                  {...fieldTheme}
                  placeholder={t("profile.namePlaceholderRedesign")}
                  placeholderTextColor={MUTED}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  autoCapitalize="words"
                  returnKeyType="next"
                  onSubmitEditing={() =>
                    setDistrictPickerRequest((request) => request + 1)
                  }
                  error={
                    fieldState.error
                      ? t(fieldState.error.message ?? "")
                      : undefined
                  }
                  leftAccessory={<UserRound size={23} color={GREEN} />}
                />
              </ProfileFieldLabel>
            )}
          />
        </ProfileSection>

        <ProfileSection title={t("profile.farmLocation")}>
          <Controller
            control={control}
            name="district"
            render={({ field: { onChange, value }, fieldState }) => (
              <ProfileFieldLabel label={t("profile.district")}>
                <AgDistrictDropdown
                  placeholder={t("profile.selectDistrict")}
                  value={value}
                  onChange={(districtId) => {
                    if (districtId !== value) {
                      setValue("block", "", { shouldDirty: true });
                      setValue("village", "", { shouldDirty: true });
                    }
                    onChange(districtId);
                  }}
                  openRequest={districtPickerRequest}
                  error={
                    fieldState.error
                      ? t(fieldState.error.message ?? "")
                      : undefined
                  }
                  leftAccessory={<MapPinned size={23} color={GREEN} />}
                  fieldStyle={styles.field}
                  textStyle={[
                    styles.inputText,
                    !value && styles.placeholderText,
                  ]}
                />
              </ProfileFieldLabel>
            )}
          />

          <View
            style={[
              styles.localityRow,
              useStackedLocalityFields && styles.localityColumn,
            ]}
          >
            <View style={styles.localityField}>
              <Controller
                control={control}
                name="block"
                render={({ field: { onChange, onBlur, value } }) => (
                  <ProfileFieldLabel label={t("profile.block")}>
                    <AgInput
                      {...fieldTheme}
                      placeholder={t("profile.blockSelectPlaceholder")}
                      placeholderTextColor={MUTED}
                      value={value}
                      onChangeText={onChange}
                      onBlur={onBlur}
                      returnKeyType="next"
                      onSubmitEditing={() => villageRef.current?.focus()}
                      leftAccessory={<Map size={22} color={GREEN} />}
                    />
                  </ProfileFieldLabel>
                )}
              />
            </View>
            <View style={styles.localityField}>
              <Controller
                control={control}
                name="village"
                render={({ field: { onChange, onBlur, value } }) => (
                  <ProfileFieldLabel label={t("profile.village")}>
                    <AgInput
                      {...fieldTheme}
                      ref={villageRef}
                      placeholder={t("profile.villagePlaceholder")}
                      placeholderTextColor={MUTED}
                      value={value}
                      onChangeText={onChange}
                      onBlur={onBlur}
                      returnKeyType="next"
                      onSubmitEditing={() => experienceRef.current?.focus()}
                      leftAccessory={<Home size={22} color={GREEN} />}
                    />
                  </ProfileFieldLabel>
                )}
              />
            </View>
          </View>
        </ProfileSection>

        <ProfileSection title={t("profile.yourFarming")}>
          <View
            style={[
              styles.farmingRow,
              useStackedFarmingFields && styles.localityColumn,
            ]}
          >
            <View style={styles.localityField}>
              <Controller
                control={control}
                name="experienceYears"
                render={({
                  field: { onChange, onBlur, value },
                  fieldState,
                }) => (
                  <ProfileFieldLabel label={t("profile.experience")}>
                    <AgInput
                      {...fieldTheme}
                      ref={experienceRef}
                      placeholder={t("profile.experiencePlaceholder")}
                      placeholderTextColor={MUTED}
                      keyboardType="number-pad"
                      inputMode="numeric"
                      maxLength={2}
                      value={value ?? ""}
                      onChangeText={onChange}
                      onBlur={onBlur}
                      returnKeyType="next"
                      onSubmitEditing={() => landRef.current?.focus()}
                      error={
                        fieldState.error
                          ? t(fieldState.error.message ?? "")
                          : undefined
                      }
                      leftAccessory={<CalendarDays size={23} color={GREEN} />}
                    />
                  </ProfileFieldLabel>
                )}
              />
            </View>

            <View style={styles.localityField}>
              <Controller
                control={control}
                name="landHoldingAcres"
                render={({
                  field: { onChange, onBlur, value },
                  fieldState,
                }) => (
                  <ProfileFieldLabel label={t("profile.landHolding")}>
                    <AgInput
                      {...fieldTheme}
                      ref={landRef}
                      placeholder={t("profile.landHoldingPlaceholder")}
                      placeholderTextColor={MUTED}
                      keyboardType="decimal-pad"
                      inputMode="decimal"
                      maxLength={9}
                      value={value ?? ""}
                      onChangeText={onChange}
                      onBlur={onBlur}
                      returnKeyType="done"
                      error={
                        fieldState.error
                          ? t(fieldState.error.message ?? "")
                          : undefined
                      }
                      leftAccessory={<Sprout size={23} color={GREEN} />}
                    />
                  </ProfileFieldLabel>
                )}
              />
            </View>
          </View>
        </ProfileSection>

        <ProfileSection title={t("profile.crops")}>
          <View style={styles.cropHeadingRow}>
            <AgText variant="bodySmall" style={styles.secondaryText}>
              {t("profile.cropsSelectAll")}
            </AgText>
          </View>
          <View style={styles.cropGrid}>
            {onboardingCrops.map((crop) => {
              const selected = selectedCrops.includes(crop.id);
              const CropIcon = CROP_ICONS[crop.id] ?? Sprout;
              const label = language === "ta" ? crop.ta : crop.en;
              return (
                <AgPressable
                  key={crop.id}
                  onPress={() => toggleCrop(crop.id)}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: selected }}
                  accessibilityLabel={label}
                  style={({ pressed }) => [
                    styles.cropCard,
                    useTwoColumnCropGrid && styles.cropCardTwoColumn,
                    selected && styles.cropCardSelected,
                    pressed && styles.pressed,
                  ]}
                >
                  <CropIcon
                    size={27}
                    color={selected ? GREEN : MUTED}
                    strokeWidth={1.7}
                  />
                  <AgText
                    variant="bodySmall"
                    weight={selected ? "semibold" : "medium"}
                    numberOfLines={2}
                    style={styles.cropLabel}
                  >
                    {label}
                  </AgText>
                  {selected ? (
                    <View style={styles.cropCheck}>
                      <Check size={14} color="#FFFFFF" strokeWidth={3} />
                    </View>
                  ) : null}
                </AgPressable>
              );
            })}
          </View>
        </ProfileSection>
      </View>

      <Pressable
        testID="finish-setup-button"
        onPress={onSubmit}
        disabled={!formState.isValid || complete.isPending}
        accessibilityRole="button"
        accessibilityState={{
          disabled: !formState.isValid || complete.isPending,
          busy: complete.isPending,
        }}
        style={[
          styles.finishButton,
          (!formState.isValid || complete.isPending) &&
            styles.finishButtonDisabled,
        ]}
      >
        {complete.isPending ? (
          <ActivityIndicator color={TEXT} />
        ) : (
          <>
            <AgText
              variant="bodyLarge"
              weight="semibold"
              style={styles.finishText}
            >
              {t("profile.finish")}
            </AgText>
            <ArrowRight size={23} color={TEXT} />
          </>
        )}
      </Pressable>
    </AgScreen>
  );
}

function ProfileFieldLabel({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <View>
      <AgText variant="body" weight="medium" style={styles.fieldLabel}>
        {label}
      </AgText>
      {children}
    </View>
  );
}

function ProfileSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.sectionCard}>
      <AgText variant="bodyLarge" weight="bold" style={styles.sectionTitle}>
        {title}
      </AgText>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flexGrow: 1, paddingTop: 8, paddingBottom: 30 },
  topBar: {
    minHeight: 64,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  brandRow: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
  },
  logo: { width: 58, height: 58 },
  wordmarkRow: { marginLeft: -6, flexDirection: "row", alignItems: "baseline" },
  wordmark: { color: TEXT, letterSpacing: -0.6 },
  wordmarkAI: { color: GREEN, letterSpacing: -0.6 },
  languageButton: {
    minWidth: 78,
    minHeight: 44,
    paddingHorizontal: 15,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: CARD_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  languageText: { color: TEXT },
  header: { marginTop: 22, alignItems: "flex-start" },
  eyebrow: { color: "#A16207", letterSpacing: 0.8 },
  heading: { marginTop: 7, color: TEXT, lineHeight: 38 },
  subtitle: { marginTop: 8, maxWidth: 520, color: MUTED, lineHeight: 23 },
  locationCard: {
    minHeight: 104,
    marginTop: 24,
    paddingHorizontal: 17,
    paddingVertical: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#A9C3AE",
    backgroundColor: "#EEF5EA",
    flexDirection: "row",
    alignItems: "center",
    shadowColor: "#173B2B",
    shadowOpacity: 0.12,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  locationCardStacked: { flexWrap: "wrap", rowGap: 12 },
  locationIcon: {
    width: 46,
    height: 46,
    borderRadius: 14,
    backgroundColor: CARD_BG,
    borderWidth: 1,
    borderColor: "#BFD2BF",
    alignItems: "center",
    justifyContent: "center",
  },
  locationCopy: { flex: 1, minWidth: 0, paddingRight: 10 },
  locationAction: {
    minWidth: 72,
    minHeight: 46,
    paddingHorizontal: 14,
    borderRadius: 13,
    backgroundColor: GOLD,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
  locationActionStacked: { width: "100%", minHeight: 48 },
  locationActionText: { color: TEXT },
  form: { marginTop: 14, gap: 12 },
  sectionCard: {
    padding: 15,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: "#E2DED1",
    backgroundColor: CARD_BG,
    shadowColor: "#173B2B",
    shadowOpacity: 0.05,
    shadowRadius: 7,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  sectionTitle: { color: TEXT },
  sectionContent: { marginTop: 12, gap: 14 },
  fieldLabel: { marginBottom: 7, color: TEXT },
  field: {
    minHeight: 56,
    borderRadius: 12,
    borderWidth: 1.25,
    borderColor: BORDER,
    backgroundColor: FIELD_BG,
  },
  inputText: { color: TEXT, backgroundColor: "transparent" },
  placeholderText: { color: MUTED },
  primaryText: { color: TEXT },
  locationSecondaryText: { color: MUTED, lineHeight: 20 },
  secondaryText: { color: MUTED, lineHeight: 20 },
  localityRow: { flexDirection: "row", gap: 12 },
  localityColumn: { flexDirection: "column" },
  localityField: { flex: 1, minWidth: 0 },
  farmingRow: { flexDirection: "row", gap: 12 },
  cropHeadingRow: {
    marginBottom: 0,
    flexDirection: "row",
    alignItems: "baseline",
    flexWrap: "wrap",
  },
  cropGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  cropCard: {
    width: "31%",
    minWidth: 0,
    minHeight: 82,
    paddingHorizontal: 8,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1.25,
    borderColor: BORDER,
    backgroundColor: FIELD_BG,
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  cropCardTwoColumn: { width: "48%" },
  cropCardSelected: { borderColor: LEAF_GREEN, backgroundColor: "#EFF8EC" },
  cropLabel: { color: TEXT, textAlign: "center", lineHeight: 18 },
  cropCheck: {
    position: "absolute",
    right: 7,
    top: 7,
    width: 21,
    height: 21,
    borderRadius: 11,
    backgroundColor: GREEN,
    alignItems: "center",
    justifyContent: "center",
  },
  finishButton: {
    minHeight: 58,
    marginTop: 16,
    borderRadius: 15,
    backgroundColor: GOLD,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  finishButtonDisabled: { opacity: 0.48 },
  finishText: { color: TEXT },
  pressed: { opacity: 0.8 },
});
