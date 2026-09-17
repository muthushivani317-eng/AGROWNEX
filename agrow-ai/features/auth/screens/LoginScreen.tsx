import { zodResolver } from "@hookform/resolvers/zod";
import { type Href, useRouter } from "expo-router";
import { ArrowRight, Phone, ShieldCheck, Sprout } from "lucide-react-native";
import { useEffect, useRef } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { StyleSheet, TextInput, useWindowDimensions, View } from "react-native";

import { AgButton, AgInput, AgScreen, AgText } from "@/components/ui";
import { buildProfile, isFirebaseConfigured } from "@/config/env";

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
  const { t } = useTranslation();
  const router = useRouter();
  const { height } = useWindowDimensions();
  const sendOtp = useSendOtp();
  const availabilityMessageKey = authAvailabilityMessageKey(
    isFirebaseConfigured,
    buildProfile,
  );
  const phoneInputRef = useRef<TextInput>(null);
  const heroHeight = Math.min(310, Math.max(250, height * 0.3));

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

  return (
    <AgScreen
      testID="phone-login-screen"
      scroll
      keyboardAvoiding
      padded={false}
      backgroundColor={LOGIN_COLORS.canvas}
      contentContainerStyle={styles.screen}
    >
      <AuthHero height={heroHeight} showLanguageSelector />

      <View style={styles.lowerSection}>
        <View style={styles.fieldContourBack} pointerEvents="none" />
        <View style={styles.fieldContourFront} pointerEvents="none" />
        <View style={styles.formContent}>
          <AgText variant="headingL" weight="bold" style={styles.title}>
            {t("auth.loginTitle")}
          </AgText>
          <AgText variant="body" style={styles.subtitle}>
            {t("auth.loginSubtitle")}
          </AgText>

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
                rightAccessory={<Phone size={21} color={LOGIN_COLORS.primary} />}
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

          <AgText variant="caption" style={styles.otpHint}>
            {t("auth.otpSupport")}
          </AgText>
          <AgButton
            title={t("auth.sendOtp")}
            onPress={onSubmit}
            loading={sendOtp.isPending}
            disabled={!formState.isValid || sendOtp.isPending}
            size="lg"
            light
            rightIcon={<ArrowRight size={20} color={LOGIN_COLORS.onAction} />}
            className="mt-5"
          />

          <View style={styles.farmerPromise}>
            <View
              style={styles.infoIcon}
              accessible={false}
              accessibilityElementsHidden
              importantForAccessibility="no-hide-descendants"
            >
              <Sprout size={24} color={LOGIN_COLORS.primary} />
            </View>
            <View style={styles.infoCopy}>
              <AgText weight="semibold" style={styles.infoTitle}>
                {t("auth.freeForFarmers")}
              </AgText>
              <AgText variant="bodySmall" style={styles.infoBody}>
                {t("auth.freeForFarmersBody")}
              </AgText>
            </View>
          </View>

          <View style={styles.privacy}>
            <View
              style={styles.infoIcon}
              accessible={false}
              accessibilityElementsHidden
              importantForAccessibility="no-hide-descendants"
            >
              <ShieldCheck size={22} color={LOGIN_COLORS.primary} />
            </View>
            <View style={styles.infoCopy}>
              <AgText variant="bodySmall" weight="semibold" style={styles.privacyText}>
                {t("auth.privacyTitle")}
              </AgText>
            </View>
          </View>
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
    marginTop: -42,
    paddingTop: 64,
    paddingBottom: 24,
    borderTopLeftRadius: 44,
    borderTopRightRadius: 44,
    overflow: "hidden",
    backgroundColor: LOGIN_COLORS.canvas,
  },
  formContent: {
    zIndex: 2,
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    paddingHorizontal: 24,
  },
  fieldContourBack: {
    position: "absolute",
    top: 18,
    left: -28,
    width: "118%",
    height: 50,
    borderTopWidth: 1,
    borderColor: "#A7C98E",
    borderRadius: 999,
    transform: [{ rotate: "2deg" }],
  },
  fieldContourFront: {
    position: "absolute",
    top: 30,
    right: -35,
    width: "110%",
    height: 44,
    borderTopWidth: 1,
    borderColor: "#D2E0C8",
    borderRadius: 999,
    transform: [{ rotate: "-2deg" }],
  },
  title: { marginBottom: 5, color: LOGIN_COLORS.ink },
  subtitle: { marginBottom: 28, color: LOGIN_COLORS.muted },
  fieldLabel: { color: LOGIN_COLORS.ink },
  phoneField: { backgroundColor: LOGIN_COLORS.surface },
  phoneInput: { color: LOGIN_COLORS.ink, backgroundColor: LOGIN_COLORS.surface },
  countryCode: { paddingRight: 13, marginRight: 4, borderRightWidth: 1 },
  countryCodeText: { color: LOGIN_COLORS.ink },
  otpHint: { marginTop: 10, color: LOGIN_COLORS.muted },
  devHint: { marginTop: 8, color: LOGIN_COLORS.muted },
  farmerPromise: {
    marginTop: 24,
    paddingVertical: 8,
    flexDirection: "row",
    alignItems: "center",
  },
  privacy: {
    marginTop: 8,
    paddingVertical: 8,
    flexDirection: "row",
    alignItems: "center",
  },
  infoIcon: {
    width: 48,
    height: 48,
    borderWidth: 1,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    borderColor: LOGIN_COLORS.primary,
    backgroundColor: "#EEF5EA",
  },
  infoCopy: { flex: 1, marginLeft: 12, gap: 2 },
  infoTitle: { color: LOGIN_COLORS.primary },
  infoBody: { color: LOGIN_COLORS.muted },
  privacyText: { color: LOGIN_COLORS.ink },
});
