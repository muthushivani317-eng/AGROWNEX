import { zodResolver } from "@hookform/resolvers/zod";
import { type Href, useRouter } from "expo-router";
import { ArrowRight, ShieldCheck, Sprout } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Keyboard, StyleSheet, TextInput, useWindowDimensions, View } from "react-native";

import { AgButton, AgInput, AgScreen, AgText } from "@/components/ui";
import { buildProfile, isFirebaseConfigured } from "@/config/env";
import { PRIVACY_POLICY_URL } from "@/config/legal";
import { openExternalUrl } from "@/lib/safeLinks";

import { authErrorMessage } from "../authMessages";
import { AuthErrorBanner } from "../components/AuthErrorBanner";
import { AuthHero } from "../components/AuthHero";
import { useSendOtp } from "../hooks/useAuthActions";
import { sanitizeIndianPhoneInput } from "../phone";
import { phoneSchema, type PhoneForm } from "../schemas";
import { authAvailabilityMessageKey } from "../services/authProvider";

const LOGIN_COLORS = {
  canvas: "#F7F4E8",
  surface: "#FFFDF8",
  ink: "#163F2E",
  muted: "#5E6B63",
  border: "#C8D2C6",
  primary: "#176B3A",
  onAction: "#101713",
};

export function LoginScreen() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const { height } = useWindowDimensions();
  const [keyboardVisible, setKeyboardVisible] = useState(false);
  const sendOtp = useSendOtp();
  const availabilityMessageKey = authAvailabilityMessageKey(
    isFirebaseConfigured,
    buildProfile,
  );
  const phoneInputRef = useRef<TextInput>(null);
  const heroHeight = keyboardVisible
    ? 148
    : Math.min(320, Math.max(260, height * 0.34));

  const { control, handleSubmit, formState } = useForm<PhoneForm>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { phone: "" },
    mode: "onChange",
  });

  const onSubmit = handleSubmit(({ phone }) => {
    if (sendOtp.isPending) return;
    sendOtp.mutate(phone, {
      onSuccess: () => router.push("/(auth)/otp" as Href),
    });
  });

  const sendOtpErrorMessage = sendOtp.isError
    ? authErrorMessage(t, sendOtp.error, "send")
    : null;

  useEffect(() => {
    if (sendOtp.isError) phoneInputRef.current?.focus();
  }, [sendOtp.isError]);

  useEffect(() => {
    const showSubscription = Keyboard.addListener("keyboardDidShow", () => {
      setKeyboardVisible(true);
    });
    const hideSubscription = Keyboard.addListener("keyboardDidHide", () => {
      setKeyboardVisible(false);
    });

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
    };
  }, []);

  return (
    <AgScreen
      testID="phone-login-screen"
      scroll
      keyboardAvoiding
      padded={false}
      backgroundColor={LOGIN_COLORS.canvas}
      contentContainerStyle={styles.screen}
    >
      <AuthHero
        height={heroHeight}
        showLanguageSelector
        showWelcome={!keyboardVisible}
      />

      <View style={styles.lowerSection}>
        <View style={styles.formContent}>
          <View style={styles.formHeading}>
            <View
              style={styles.sproutBadge}
              accessible={false}
              accessibilityElementsHidden
              importantForAccessibility="no-hide-descendants"
            >
              <Sprout size={26} color={LOGIN_COLORS.primary} />
            </View>
            <View style={styles.formHeadingCopy}>
              <AgText variant="headingL" weight="bold" style={styles.title}>
                {t("auth.getStarted")}
              </AgText>
              <AgText variant="body" style={styles.subtitle}>
                {t("auth.phoneEntrySubtitle")}
              </AgText>
            </View>
          </View>

          <Controller
            control={control}
            name="phone"
            render={({ field: { onChange, onBlur, value }, fieldState }) => (
              <AgInput
                ref={phoneInputRef}
                testID="phone-number-input"
                label={t("auth.phoneLabel")}
                placeholder={t("auth.phonePlaceholder")}
                keyboardType="phone-pad"
                inputMode="tel"
                editable
                showSoftInputOnFocus
                textContentType="telephoneNumber"
                autoComplete="tel"
                maxLength={16}
                value={value}
                onChangeText={(text) =>
                  onChange(sanitizeIndianPhoneInput(text))
                }
                onBlur={onBlur}
                error={
                  fieldState.error
                    ? t(fieldState.error.message ?? "")
                    : undefined
                }
                fieldBackgroundColor={LOGIN_COLORS.surface}
                fieldBorderColor={LOGIN_COLORS.border}
                focusBorderColor={LOGIN_COLORS.primary}
                fieldStyle={styles.phoneField}
                labelStyle={styles.fieldLabel}
                style={styles.phoneInput}
                leftAccessory={
                  <View
                    style={[styles.countryCode, { borderColor: LOGIN_COLORS.border }]}
                  >
                    <AgText weight="semibold" style={styles.countryCodeText}>+91</AgText>
                  </View>
                }
                returnKeyType="done"
                onSubmitEditing={onSubmit}
              />
            )}
          />

          {sendOtpErrorMessage ? (
            <AuthErrorBanner
              testID="otp-send-error"
              message={sendOtpErrorMessage}
            />
          ) : null}
          {availabilityMessageKey ? (
            <AgText variant="caption" style={styles.devHint}>
              {t(availabilityMessageKey)}
            </AgText>
          ) : null}

          <View style={styles.sendOtpAction}>
            <AgButton
              title={t("auth.sendOtp")}
              onPress={onSubmit}
              loading={sendOtp.isPending}
              disabled={!formState.isValid || sendOtp.isPending}
              size="lg"
              variant="success"
              light
              rightIcon={<ArrowRight size={22} color="#FFFFFF" />}
            />
          </View>

          <View style={styles.otpReassurance}>
            <View
              style={styles.reassuranceIcon}
              accessible={false}
              accessibilityElementsHidden
              importantForAccessibility="no-hide-descendants"
            >
              <ShieldCheck size={19} color={LOGIN_COLORS.primary} />
            </View>
            <AgText variant="caption" style={styles.otpHint}>
              {t("auth.otpSupport")}
            </AgText>
          </View>

          {/* Notice at collection (DPDP Act): shown before the phone number is sent. */}
          <AgText variant="caption" center style={styles.legalNotice} testID="login-privacy-notice">
            {t("auth.consentNotice")}{" "}
            <AgText
              variant="caption"
              weight="semibold"
              style={styles.legalLink}
              accessibilityRole="link"
              onPress={() =>
                void openExternalUrl(`${PRIVACY_POLICY_URL}?lang=${i18n.language === "ta" ? "ta" : "en"}`)
              }
            >
              {t("settings.privacyPolicy")}
            </AgText>
          </AgText>

          {!keyboardVisible ? (
            <View style={styles.benefits}>
              <View style={styles.benefit}>
                <View style={styles.benefitIcon} accessible={false}>
                  <Sprout size={22} color={LOGIN_COLORS.primary} />
                </View>
                <AgText variant="caption" weight="semibold" style={styles.benefitTitle}>
                  {t("auth.freeForFarmers")}
                </AgText>
              </View>
              <View style={styles.benefitDivider} />
              <View style={styles.benefit}>
                <View style={styles.benefitIcon} accessible={false}>
                  <ShieldCheck size={22} color={LOGIN_COLORS.primary} />
                </View>
                <AgText variant="caption" weight="semibold" style={styles.benefitTitle}>
                  {t("auth.privacyTitle")}
                </AgText>
              </View>
            </View>
          ) : null}
        </View>
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { flexGrow: 1, paddingBottom: 0 },
  lowerSection: {
    flexGrow: 1,
    width: "100%",
    marginTop: -22,
    paddingTop: 22,
    paddingHorizontal: 18,
    paddingBottom: 34,
    backgroundColor: LOGIN_COLORS.canvas,
  },
  formContent: {
    zIndex: 2,
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    padding: 22,
    borderRadius: 24,
    backgroundColor: LOGIN_COLORS.surface,
    shadowColor: "#306541",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.12,
    shadowRadius: 24,
    elevation: 5,
  },
  formHeading: { flexDirection: "row", alignItems: "center", marginBottom: 22 },
  sproutBadge: {
    width: 50,
    height: 50,
    borderRadius: 25,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EDF6E9",
  },
  formHeadingCopy: { flex: 1, marginLeft: 13 },
  title: { color: LOGIN_COLORS.ink },
  subtitle: { marginTop: 3, color: LOGIN_COLORS.muted, lineHeight: 21 },
  fieldLabel: { marginBottom: 8, color: LOGIN_COLORS.ink },
  phoneField: { backgroundColor: LOGIN_COLORS.surface },
  phoneInput: { color: LOGIN_COLORS.ink, backgroundColor: LOGIN_COLORS.surface },
  countryCode: { paddingRight: 13, marginRight: 4, borderRightWidth: 1 },
  countryCodeText: { color: LOGIN_COLORS.ink },
  // Keep the primary action visually separate from the phone field. The
  // previous NativeWind utility was superseded by AgButton's inline style.
  sendOtpAction: { marginTop: 16 },
  otpHint: { flex: 1, color: LOGIN_COLORS.muted, lineHeight: 18 },
  devHint: { marginTop: 8, color: LOGIN_COLORS.muted },
  otpReassurance: {
    marginTop: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
  reassuranceIcon: { marginRight: 8 },
  legalNotice: { marginTop: 12, color: LOGIN_COLORS.muted, lineHeight: 18 },
  legalLink: { color: LOGIN_COLORS.primary, textDecorationLine: "underline" },
  benefits: {
    marginTop: 30,
    paddingTop: 22,
    borderTopWidth: 1,
    borderTopColor: "#E3E8DF",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
  benefit: { flex: 1, alignItems: "center", gap: 8 },
  benefitIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EEF5EA",
  },
  benefitTitle: { color: LOGIN_COLORS.ink, textAlign: "center", lineHeight: 17 },
  benefitDivider: { width: 1, height: 52, backgroundColor: "#E3E8DF" },
});
