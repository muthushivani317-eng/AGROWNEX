// Evidence Pack detail/download/share screen. Renders whatever the pack
// actually has -- imagery sections simply don't render when
// `has_pre_event_imagery`/`has_post_event_imagery` are false, rather than
// showing a broken image placeholder. At MVP the backend always returns
// both flags as false (rendered-scene lookup isn't wired up yet -- see the
// integration report), so this screen only ever shows the text content
// today; the image-rendering branches are left in place; ready for when
// that backend capability lands.
import { useLocalSearchParams } from "expo-router";
import { Download, Share2, Users } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AgButton, AgErrorState, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { useEvidencePack, useShareEvidencePack } from "../hooks/useDailyTask";
import type { EvidencePackShareTarget } from "../types";
import { openExternalUrl } from "@/lib/safeLinks";

const CONFIDENCE_LABEL_KEY: Record<string, string> = {
  high: "dailyTask.confidenceHigh",
  medium: "dailyTask.confidenceMedium",
  limited: "dailyTask.confidenceLimited",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <AgText variant="body" weight="semibold" style={styles.sectionTitle}>
        {title}
      </AgText>
      {children}
    </View>
  );
}

export function EvidencePackScreen() {
  const { packId } = useLocalSearchParams<{ packId: string }>();
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { data: pack, isLoading, isError, refetch } = useEvidencePack(packId);
  const share = useShareEvidencePack(packId ?? "");
  const [pendingTarget, setPendingTarget] = useState<EvidencePackShareTarget | null>(null);

  const handleShare = async (target: EvidencePackShareTarget) => {
    if (!pack) return;
    setPendingTarget(target);
    try {
      await share.mutateAsync({ shareWith: target });
      if (target === "self_download" && pack.pdf_download_url) {
        await openExternalUrl(pack.pdf_download_url);
      }
    } finally {
      setPendingTarget(null);
    }
  };

  if (isLoading || !pack) {
    return (
      <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
        <View style={styles.centered}>
          {isError ? <AgErrorState onRetry={refetch} /> : <ActivityIndicator size="large" />}
        </View>
      </SafeAreaView>
    );
  }

  const { content } = pack;
  const sharing = share.isPending;

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <AgText variant="headingS" weight="bold" style={{ color: colors.text, marginBottom: 2 }}>
          {t("dailyTask.evidencePackTitle")}
        </AgText>
        <AgText variant="body" style={{ color: colors.textMuted, marginBottom: 16 }}>
          {content.farmer_name}
        </AgText>

        <View style={[styles.confidencePill, { backgroundColor: `${colors.info}18` }]}>
          <AgText variant="body" weight="semibold" style={{ color: colors.info }}>
            {t(CONFIDENCE_LABEL_KEY[pack.confidence_level])}
          </AgText>
        </View>

        {pack.status === "pending_post_event_data" ? (
          <View style={[styles.noticeBox, { backgroundColor: `${colors.warning}18` }]}>
            <AgText variant="body" style={{ color: colors.warning }}>
              {t("dailyTask.evidencePackPendingNotice")}
            </AgText>
          </View>
        ) : null}

        <Section title={t("dailyTask.evidencePackBeforeSection")}>
          <AgText variant="body" style={{ color: colors.text }}>
            {content.pre_event_trend_summary_ta}
          </AgText>
          {pack.has_pre_event_imagery && content.pre_event_scan_date ? (
            <Image source={{ uri: `evidence-pack-image://${pack.id}/pre` }} style={styles.image} />
          ) : null}
        </Section>

        <Section title={t("dailyTask.evidencePackAfterSection")}>
          <AgText variant="body" style={{ color: colors.text }}>
            {content.post_event_trend_summary_ta}
          </AgText>
          {pack.has_post_event_imagery && content.post_event_scan_date ? (
            <Image source={{ uri: `evidence-pack-image://${pack.id}/post` }} style={styles.image} />
          ) : null}
        </Section>

        {content.standing_water_note_ta ? (
          <Section title={t("dailyTask.evidencePackStandingWaterSection")}>
            <AgText variant="body" style={{ color: colors.text }}>
              {content.standing_water_note_ta}
            </AgText>
          </Section>
        ) : null}

        <Section title={t("dailyTask.evidencePackWeatherSection")}>
          <AgText variant="body" style={{ color: colors.text }}>
            {content.weather_context_ta}
          </AgText>
        </Section>

        {content.farmer_photo_object_ids.length > 0 ? (
          <Section title={t("dailyTask.evidencePackPhotosSection")}>
            <View style={styles.photoGrid}>
              {content.farmer_photo_object_ids.map((id) => (
                <Image key={id} source={{ uri: `farmer-photo://${id}` }} style={styles.photoThumb} />
              ))}
            </View>
          </Section>
        ) : null}

        <View style={[styles.disclaimerBox, { backgroundColor: colors.card, borderColor: colors.border }]}>
          <AgText variant="bodySmall" style={{ color: colors.textMuted }}>
            {content.disclaimer_ta}
          </AgText>
        </View>

        <View style={styles.actions}>
          <AgButton
            title={t("dailyTask.shareWithFpo")}
            onPress={() => handleShare("fpo")}
            loading={sharing && pendingTarget === "fpo"}
            disabled={sharing}
            leftIcon={<Users size={18} color={colors.onPrimary} />}
            fullWidth
          />
          <AgButton
            title={t("dailyTask.downloadPdf")}
            onPress={() => handleShare("self_download")}
            loading={sharing && pendingTarget === "self_download"}
            disabled={sharing || !pack.pdf_download_url}
            variant="secondary"
            leftIcon={<Download size={18} color={colors.text} />}
            fullWidth
          />
          <AgButton
            title={t("dailyTask.shareExternal")}
            onPress={() => handleShare("external")}
            loading={sharing && pendingTarget === "external"}
            disabled={sharing}
            variant="outline"
            leftIcon={<Share2 size={18} color={colors.primary} />}
            fullWidth
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  content: { padding: 20 },
  confidencePill: { alignSelf: "flex-start", borderRadius: 14, paddingHorizontal: 14, paddingVertical: 8, marginBottom: 20 },
  noticeBox: { borderRadius: 14, padding: 14, marginBottom: 20 },
  section: { marginBottom: 20 },
  sectionTitle: { marginBottom: 8 },
  image: { width: "100%", height: 180, borderRadius: 12, marginTop: 8 },
  photoGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  photoThumb: { width: 90, height: 90, borderRadius: 8 },
  disclaimerBox: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 20 },
  actions: { gap: 12 },
});
