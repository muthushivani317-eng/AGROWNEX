import { Image } from "expo-image";
import { useRouter } from "expo-router";
import { ArrowRight, Check, ShieldCheck } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useLanguage } from "@/hooks/useLanguage";
import type { SupportedLanguage } from "@/types";
import { useAuthStore } from "../store/authStore";

const COLORS = {
  background: "#F7F4E8",
  surface: "#FFFDF8",
  surfaceSelected: "#E8F3E5",
  border: "#D9D6C8",
  borderSelected: "#176B3A",
  primary: "#176B3A",
  primaryBright: "#78DB50",
  accent: "#D99A19",
  text: "#163F2E",
  muted: "#5E6B63",
  onPrimary: "#071008",
};

const OPTIONS: {
  value: SupportedLanguage;
  badge: string;
  title: string;
  subtitleKey: "language.tamil" | "language.english";
}[] = [
  { value: "ta", badge: "அ", title: "தமிழ்", subtitleKey: "language.tamil" },
  {
    value: "en",
    badge: "EN",
    title: "English",
    subtitleKey: "language.english",
  },
];

/** First-run language selection. The existing setter persists immediately. */
export function LanguageSelectScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { language, setLanguage } = useLanguage();
  const { height, width } = useWindowDimensions();
  const compact = height < 740 || width < 360;
  const [selected, setSelected] = useState<SupportedLanguage>(language ?? "ta");
  const [isApplying, setIsApplying] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const confirmLanguageSelection = useAuthStore(
    (state) => state.confirmLanguageSelection,
  );

  const choose = async (lng: SupportedLanguage) => {
    if (isApplying) return;
    const previous = selected;
    setSelected(lng);
    setSaveError(false);
    setIsApplying(true);
    try {
      await setLanguage(lng);
    } catch {
      setSelected(previous);
      setSaveError(true);
    } finally {
      setIsApplying(false);
    }
  };

  const continueToLogin = () => {
    if (isApplying) return;
    confirmLanguageSelection();
    router.replace("/(auth)/login");
  };

  return (
    <SafeAreaView
      testID="language-selection-screen"
      edges={["top", "bottom"]}
      style={styles.safeArea}
    >
      <ScrollView
        contentContainerStyle={styles.screen}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View
          pointerEvents="none"
          accessible={false}
          importantForAccessibility="no-hide-descendants"
          style={styles.farmArtwork}
        >
          <View style={[styles.fieldLine, styles.fieldLineOne]} />
          <View style={[styles.fieldLine, styles.fieldLineTwo]} />
          <View style={[styles.fieldLine, styles.fieldLineThree]} />
          <View style={styles.sunLine} />
        </View>

        <View
          accessible
          style={[styles.brand, compact && styles.brandCompact]}
          accessibilityLabel={`${t("language.tagline")}, AgrowAI`}
        >
          <View
            style={[styles.logoSurface, compact && styles.logoSurfaceCompact]}
          >
            <Image
              accessible={false}
              source={require("../../../assets/images/android-icon-foreground.png")}
              style={[styles.logo, compact && styles.logoCompact]}
              contentFit="contain"
              transition={0}
            />
          </View>
          <View
            style={[styles.wordmarkRow, compact && styles.wordmarkRowCompact]}
          >
            <Text style={[styles.wordmark, compact && styles.wordmarkCompact]}>
              Agrow
            </Text>
            <Text
              style={[styles.wordmarkAI, compact && styles.wordmarkCompact]}
            >
              AI
            </Text>
          </View>
          <Text style={styles.tagline}>{t("language.tagline")}</Text>
        </View>

        <View style={[styles.hero, compact && styles.heroCompact]}>
          <Text
            style={[styles.title, compact && styles.titleCompact]}
            maxFontSizeMultiplier={1.35}
          >
            {t("language.title")}
          </Text>
          <View style={styles.titleAccent} />
          <Text style={styles.subtitle} maxFontSizeMultiplier={1.4}>
            {t("language.subtitle")}
          </Text>
        </View>

        <View accessibilityRole="radiogroup" style={styles.options}>
          {OPTIONS.map((option) => {
            const active = selected === option.value;
            return (
              <TouchableOpacity
                key={option.value}
                testID={`language-option-${option.value}`}
                onPress={() => void choose(option.value)}
                disabled={isApplying}
                activeOpacity={0.78}
                accessibilityRole="radio"
                accessibilityState={{ checked: active, selected: active }}
                accessibilityLabel={`${option.title}, ${t(option.subtitleKey)}`}
                style={[
                  styles.optionCard,
                  compact && styles.optionCardCompact,
                  active && styles.optionCardSelected,
                ]}
              >
                <View
                  style={[
                    styles.languageBadge,
                    compact && styles.languageBadgeCompact,
                    active && styles.languageBadgeSelected,
                  ]}
                >
                  <Text
                    style={[
                      styles.badgeText,
                      option.value === "ta" && styles.tamilText,
                      active && styles.badgeTextSelected,
                    ]}
                  >
                    {option.badge}
                  </Text>
                </View>
                <View style={styles.optionCopy}>
                  <Text
                    style={[
                      styles.optionTitle,
                      option.value === "ta" && styles.tamilText,
                    ]}
                  >
                    {option.title}
                  </Text>
                  <Text style={styles.optionSubtitle}>
                    {t(option.subtitleKey)}
                  </Text>
                </View>
                <View
                  testID={`language-indicator-${option.value}`}
                  style={[styles.radio, active && styles.radioSelected]}
                >
                  {active ? (
                    <Check size={22} strokeWidth={3} color={COLORS.onPrimary} />
                  ) : null}
                </View>
              </TouchableOpacity>
            );
          })}
        </View>

        {saveError ? (
          <View accessibilityRole="alert" style={styles.errorBanner}>
            <Text style={styles.errorText}>{t("language.changeFailed")}</Text>
          </View>
        ) : null}

        <TouchableOpacity
          testID="language-continue"
          onPress={continueToLogin}
          activeOpacity={0.78}
          accessibilityRole="button"
          accessibilityState={{ disabled: isApplying }}
          accessibilityLabel={t("common.continue")}
          disabled={isApplying}
          style={[
            styles.continueButton,
            isApplying && styles.continueButtonDisabled,
          ]}
        >
          {isApplying ? (
            <ActivityIndicator color={COLORS.onPrimary} />
          ) : (
            <>
              <Text style={styles.continueText}>{t("common.continue")}</Text>
              <ArrowRight size={26} strokeWidth={2.5} color={COLORS.onPrimary} />
            </>
          )}
        </TouchableOpacity>

        <View style={styles.trustRow}>
          <ShieldCheck size={22} color={COLORS.primary} />
          <Text style={styles.trustText}>{t("language.trust")}</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: COLORS.background },
  screen: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 24,
  },
  farmArtwork: {
    position: "absolute",
    top: 84,
    left: 0,
    right: 0,
    height: 170,
    opacity: 0.18,
    overflow: "hidden",
  },
  fieldLine: {
    position: "absolute",
    left: "-10%",
    width: "120%",
    height: 110,
    borderWidth: 1,
    borderColor: "#70A679",
    borderRadius: 220,
  },
  fieldLineOne: { top: 54, transform: [{ rotate: "-5deg" }] },
  fieldLineTwo: { top: 84, transform: [{ rotate: "5deg" }] },
  fieldLineThree: { top: 112, transform: [{ rotate: "-2deg" }] },
  sunLine: {
    position: "absolute",
    top: 35,
    alignSelf: "center",
    width: 48,
    height: 24,
    borderTopLeftRadius: 48,
    borderTopRightRadius: 48,
    borderWidth: 1,
    borderBottomWidth: 0,
    borderColor: "#70A679",
  },
  brand: { alignItems: "center", marginBottom: 20 },
  brandCompact: { marginBottom: 14 },
  logoSurface: {
    width: 104,
    height: 104,
    borderRadius: 28,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: "#C9D9C7",
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#173B2B",
    shadowOpacity: 0.1,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 5 },
    elevation: 3,
  },
  logoSurfaceCompact: { width: 86, height: 86, borderRadius: 24 },
  logo: { width: 96, height: 96 },
  logoCompact: { width: 80, height: 80 },
  wordmarkRow: { marginTop: 12, flexDirection: "row", alignItems: "baseline" },
  wordmarkRowCompact: { marginTop: 7 },
  wordmark: {
    color: COLORS.text,
    fontFamily: "Inter_700Bold",
    fontSize: 36,
    lineHeight: 42,
    letterSpacing: -1.2,
  },
  wordmarkAI: {
    color: COLORS.primary,
    fontFamily: "Inter_700Bold",
    fontSize: 36,
    lineHeight: 42,
    letterSpacing: -1.2,
  },
  wordmarkCompact: { fontSize: 31, lineHeight: 37 },
  tagline: {
    color: COLORS.primary,
    fontFamily: "NotoSansTamil_500Medium",
    fontSize: 15,
    lineHeight: 23,
    marginTop: 2,
    textAlign: "center",
  },
  hero: { alignItems: "center", marginBottom: 22 },
  heroCompact: { marginBottom: 16 },
  title: {
    color: COLORS.text,
    fontFamily: "NotoSansTamil_700Bold",
    fontSize: 30,
    lineHeight: 42,
    paddingHorizontal: 8,
    textAlign: "center",
  },
  titleCompact: { fontSize: 27, lineHeight: 36 },
  titleAccent: {
    width: 52,
    height: 3,
    borderRadius: 2,
    backgroundColor: COLORS.accent,
    marginTop: 12,
  },
  subtitle: {
    color: COLORS.muted,
    fontFamily: "NotoSansTamil_400Regular",
    fontSize: 16,
    lineHeight: 25,
    marginTop: 12,
    maxWidth: 340,
    textAlign: "center",
  },
  options: { width: "100%", gap: 12 },
  errorBanner: {
    width: "100%",
    marginTop: 14,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#E2A6A1",
    backgroundColor: "#FFF0EE",
  },
  errorText: {
    color: "#8B2E28",
    fontFamily: "NotoSansTamil_500Medium",
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  optionCard: {
    width: "100%",
    minHeight: 104,
    paddingHorizontal: 18,
    paddingVertical: 16,
    borderRadius: 22,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    backgroundColor: COLORS.surface,
    flexDirection: "row",
    alignItems: "center",
  },
  optionCardCompact: {
    minHeight: 88,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  optionCardSelected: {
    borderColor: COLORS.borderSelected,
    backgroundColor: COLORS.surfaceSelected,
    shadowColor: "#176B3A",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  languageBadge: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EEF1EA",
    borderWidth: 1,
    borderColor: "#D4DDD1",
  },
  languageBadgeCompact: { width: 56, height: 56, borderRadius: 28 },
  languageBadgeSelected: {
    backgroundColor: COLORS.primaryBright,
    borderColor: COLORS.primaryBright,
  },
  badgeText: {
    color: COLORS.primary,
    fontFamily: "Inter_700Bold",
    fontSize: 25,
    lineHeight: 32,
  },
  badgeTextSelected: { color: COLORS.onPrimary },
  tamilText: { fontFamily: "NotoSansTamil_700Bold" },
  optionCopy: { flex: 1, minWidth: 0, paddingHorizontal: 16 },
  optionTitle: {
    color: COLORS.text,
    fontFamily: "Inter_700Bold",
    fontSize: 22,
    lineHeight: 30,
  },
  optionSubtitle: {
    color: COLORS.muted,
    fontFamily: "NotoSansTamil_400Regular",
    fontSize: 15,
    lineHeight: 23,
    marginTop: 2,
  },
  radio: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 2,
    borderColor: "#87928B",
    alignItems: "center",
    justifyContent: "center",
  },
  radioSelected: {
    backgroundColor: COLORS.primaryBright,
    borderColor: COLORS.primaryBright,
  },
  continueButton: {
    width: "100%",
    minHeight: 58,
    borderRadius: 18,
    backgroundColor: COLORS.primaryBright,
    marginTop: 24,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    opacity: 1,
    shadowColor: "#176B3A",
    shadowOpacity: 0.14,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  continueText: {
    color: COLORS.onPrimary,
    fontFamily: "NotoSansTamil_700Bold",
    fontSize: 20,
    lineHeight: 28,
  },
  continueButtonDisabled: { opacity: 0.62 },
  trustRow: {
    marginTop: 18,
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
  },
  trustText: {
    color: COLORS.muted,
    fontFamily: "NotoSansTamil_400Regular",
    fontSize: 13,
    lineHeight: 20,
    flexShrink: 1,
    textAlign: "center",
  },
});
