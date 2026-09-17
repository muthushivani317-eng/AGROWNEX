import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Camera,
  Images,
  Leaf,
  RotateCcw,
} from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  Linking,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";

import { AgButton, AgCard, AgScreen, AgText } from "@/components/ui";
import {
  captureFromCamera,
  pickFromGallery,
  type CaptureMethod,
  type PickedImage,
} from "@/features/disease";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";

import { analyzeLcc } from "./api";
import type { LccResult } from "./types";

export function LccScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { farms, selected, select, isLoading, isError, refetch } = useSelectedFarm();
  const [photo, setPhoto] = useState<PickedImage | null>(null);
  const [result, setResult] = useState<LccResult | null>(null);
  const [busy, setBusy] = useState(false);

  const choose = async (method: CaptureMethod) => {
    const picked =
      method === "camera" ? await captureFromCamera() : await pickFromGallery();
    if (picked) {
      setPhoto(picked);
      setResult(null);
    }
  };

  const analyze = async () => {
    if (busy) return;
    if (!selected || !photo?.base64) {
      Alert.alert(t("common.error"), t(!selected ? "lcc.farmRequired" : "lcc.analysisFailed"));
      return;
    }
    setBusy(true);
    try {
      setResult(
        await analyzeLcc({
          farmId: selected.id,
          imageBase64: photo.base64,
          mimeType: photo.mimeType as "image/jpeg" | "image/png" | "image/webp",
        }),
      );
    } catch (error) {
      const failure = error as { response?: { status?: number }; code?: string };
      const key = failure.response?.status === 404
        ? "lcc.serviceUnavailable"
        : !failure.response && (failure.code === "ERR_NETWORK" || failure.code === "ECONNABORTED")
          ? "lcc.networkFailed"
          : "lcc.analysisFailed";
      Alert.alert(t("common.error"), t(key));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setPhoto(null);
    setResult(null);
  };

  return (
    <AgScreen scroll contentContainerStyle={styles.screen}>
      <View style={styles.header}>
        <TouchableOpacity
          accessibilityRole="button"
          onPress={() => router.back()}
        >
          <ArrowLeft size={24} color={colors.text} />
        </TouchableOpacity>
        <View style={styles.flex}>
          <AgText variant="headingM" weight="bold">
            {t("lcc.title")}
          </AgText>
          <AgText variant="bodySmall" color="muted">
            {t("lcc.subtitle")}
          </AgText>
        </View>
      </View>

      {isLoading ? <ActivityIndicator color={colors.primary} /> : null}
      {!isLoading && (isError || !selected) ? (
        <AgCard style={styles.card}>
          <AgText variant="body">{t(isError ? "lcc.farmsFailed" : "lcc.farmRequired")}</AgText>
          {isError ? <AgButton title={t("common.retry")} onPress={() => void refetch()} /> : null}
        </AgCard>
      ) : null}
      <FarmSelector
        farms={farms}
        selectedId={selected?.id ?? null}
        onSelect={select}
      />

      <AgCard style={styles.card}>
        <View style={styles.tipTitle}>
          <Leaf size={24} color={colors.primary} />
          <AgText variant="bodyLarge" weight="semibold">
            {t("lcc.photoGuideTitle")}
          </AgText>
        </View>
        <AgText variant="body">{t("lcc.photoGuide")}</AgText>
        <AgText variant="bodySmall" color="muted">
          {t("lcc.safetyNote")}
        </AgText>
      </AgCard>

      {photo ? (
        <Image
          source={{ uri: photo.uri }}
          style={styles.photo}
          contentFit="cover"
        />
      ) : null}

      {!photo ? (
        <View style={styles.actions}>
          <AgButton
            title={t("lcc.takePhoto")}
            onPress={() => choose("camera")}
            leftIcon={<Camera size={20} color="#fff" />}
          />
          <AgButton
            title={t("lcc.choosePhoto")}
            variant="outline"
            onPress={() => choose("gallery")}
            leftIcon={<Images size={20} color={colors.primary} />}
          />
        </View>
      ) : (
        <View style={styles.actions}>
          <AgButton
            title={t("lcc.analyze")}
            onPress={analyze}
            loading={busy}
            disabled={busy || !selected}
          />
          <AgButton
            title={t("lcc.retake")}
            variant="outline"
            onPress={reset}
            leftIcon={<RotateCcw size={20} color={colors.primary} />}
          />
        </View>
      )}

      {result ? (
        <AgCard style={styles.card}>
          {result.abstained ? (
            <>
              <AgText variant="headingS" weight="bold">
                {t("lcc.retakeRequired")}
              </AgText>
              <AgText variant="body">{t(result.guidance_key)}</AgText>
            </>
          ) : (
            <>
              <AgText variant="bodySmall" color="muted">
                {t("lcc.matchedPanel")}
              </AgText>
              <AgText variant="headingL" weight="bold">
                {result.panel_number}
              </AgText>
              <AgText variant="headingS" weight="bold">
                {t("lcc.educationalResult")}
              </AgText>
              <AgText variant="body">{t("lcc.educationalGuidance")}</AgText>
              <AgText variant="bodySmall" color="muted">
                {t("lcc.estimateDisclaimer")}
              </AgText>
            </>
          )}
        </AgCard>
      ) : null}
      <AgButton
        title={t("lcc.learnMore")}
        variant="outline"
        onPress={() => {
          void Linking.openURL("https://agritech.tnau.ac.in/agriculture/agri_Nutrient_mainfeild_%20Nitrogen_LCC_Rice.html")
            .catch(() => Alert.alert(t("common.error"), t("lcc.sourceUnavailable")));
        }}
      />
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { padding: 16, gap: 16 },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  flex: { flex: 1 },
  card: { gap: 10 },
  tipTitle: { flexDirection: "row", alignItems: "center", gap: 8 },
  photo: { width: "100%", height: 300, borderRadius: 16 },
  actions: { gap: 10 },
});
