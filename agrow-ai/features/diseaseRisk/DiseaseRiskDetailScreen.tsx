import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  CloudSun,
  RefreshCw,
  ShieldAlert,
  Sprout,
} from "lucide-react-native";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { AgButton, AgScreen, AgText } from "@/components/ui";
import { getRisk } from "./api";
import { farmerMessageOrFallback } from "./types";
import { diseaseRiskErrorMessageKey } from "./errors";

const C = {
  ink: "#173B2B",
  muted: "#5F6F67",
  bg: "#F8F5E9",
  paper: "#FFFDF8",
  border: "#DDD7C6",
  green: "#176B36",
  amber: "#B77908",
  amberBg: "#FFF4D8",
  greenBg: "#EAF3E5",
};

export function DiseaseRiskDetailScreen({ id }: { id: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const query = useQuery({
    queryKey: ["disease-risk", id],
    queryFn: () => getRisk(id),
    retry: false,
  });
  return (
    <AgScreen
      padded={false}
      backgroundColor={C.bg}
      testID="disease-risk-detail-screen"
    >
      <ScrollView contentContainerStyle={[styles.page, { paddingHorizontal: 20 }]}
        refreshControl={<RefreshControl refreshing={query.isFetching} onRefresh={() => { if (!query.isFetching) void query.refetch(); }} tintColor={C.green} />}>
      <View style={styles.topRow}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          onPress={() => router.back()}
          hitSlop={10}
          style={styles.backButton}
        >
          <ArrowLeft size={27} color={C.ink} />
        </Pressable>
        <View style={styles.brandIcon}>
          <ShieldAlert size={27} color={C.green} />
        </View>
        <AgText variant="label" weight="bold" style={styles.eyebrow}>
          {t("diseaseRisk.detailEyebrow")}
        </AgText>
      </View>
      <AgText variant="headingXL" weight="bold" style={styles.ink}>
        {t("diseaseRisk.detailTitle")}
      </AgText>
      <AgText variant="bodyLarge" style={styles.muted}>
        {t("diseaseRisk.detailSubtitle")}
      </AgText>
      <View style={styles.safetyCard}>
        <ShieldAlert size={23} color={C.amber} />
        <AgText style={styles.safetyCopy}>
          {t("diseaseRisk.notDiagnosis")}
        </AgText>
      </View>
      {query.isLoading ? (
        <View style={styles.stateCard}>
          <ActivityIndicator size="large" color={C.green} />
          <AgText
            variant="headingS"
            weight="semibold"
            center
            style={styles.ink}
          >
            {t("diseaseRisk.detailLoading")}
          </AgText>
        </View>
      ) : query.isError ? (
        <View style={styles.stateCard}>
          <View style={styles.errorIcon}>
            <AlertTriangle size={29} color={C.amber} />
          </View>
          <AgText
            variant="headingS"
            weight="semibold"
            center
            style={styles.ink}
          >
            {t("diseaseRisk.errorTitle")}
          </AgText>
          <AgText center style={styles.muted}>
            {t(diseaseRiskErrorMessageKey(query.error))}
          </AgText>
          <AgButton
            light
            variant="outline"
            title={t("common.retry")}
            disabled={query.isFetching}
            onPress={() => { if (!query.isFetching) void query.refetch(); }}
            leftIcon={<RefreshCw size={20} color={C.green} />}
          />
        </View>
      ) : query.data ? (
        <>
          <View style={styles.summaryCard}>
            <View style={styles.summaryTop}>
              <View style={styles.alertIcon}>
                {query.data.riskLevel || query.data.diseaseKey ? (
                  <AlertTriangle size={28} color={C.amber} />
                ) : (
                  <CheckCircle2 size={28} color={C.green} />
                )}
              </View>
              <View style={styles.flex}>
                <AgText variant="label" weight="bold" style={styles.eyebrow}>
                  {t("diseaseRisk.assessmentLabel")}
                </AgText>
                <AgText variant="headingM" weight="bold" style={styles.ink}>
                  {farmerMessageOrFallback(query.data.farmerMessageKey, t)}
                </AgText>
              </View>
            </View>
            <View style={styles.divider} />
            <InfoRow
              icon={<Sprout size={21} color={C.green} />}
              label={t("diseaseRisk.cropLabel")}
              value={query.data.crop}
            />
            <InfoRow
              icon={<CalendarClock size={21} color={C.green} />}
              label={t("diseaseRisk.checkedLabel")}
              value={query.data.generatedAt}
            />
            <InfoRow
              icon={<CloudSun size={21} color={C.green} />}
              label={t("diseaseRisk.weatherLabel")}
              value={t("diseaseRisk.source", {
                source: query.data.weatherSource,
              })}
            />
            {query.data.status === "STAGE_UNCONFIRMED" ? (
              <InfoRow
                icon={<Sprout size={21} color={C.amber} />}
                label={t("diseaseRisk.missingEvidenceLabel")}
                value={t("diseaseRisk.confirmCropStage")}
              />
            ) : null}
          </View>
          <View style={styles.guidanceCard}>
            <View style={styles.guidanceIcon}>
              <Sprout size={25} color={C.green} />
            </View>
            <View style={styles.flex}>
              <AgText variant="headingS" weight="semibold" style={styles.ink}>
                {t("diseaseRisk.nextStepTitle")}
              </AgText>
              <AgText style={styles.muted}>{t("diseaseRisk.monitor")}</AgText>
            </View>
          </View>
          <View style={styles.verificationCard}>
            <ShieldAlert size={22} color={C.amber} />
            <View style={styles.flex}>
              <AgText weight="semibold" style={styles.verificationTitle}>
                {t("diseaseRisk.verifyTitle")}
              </AgText>
              <AgText variant="bodySmall" style={styles.muted}>
                {t("diseaseRisk.verificationPending")}
              </AgText>
            </View>
          </View>
        </>
      ) : null}
      </ScrollView>
    </AgScreen>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.detailRow}>
      {icon}
      <View style={styles.flex}>
        <AgText variant="bodySmall" style={styles.muted}>
          {label}
        </AgText>
        <AgText weight="semibold" style={styles.ink}>
          {value}
        </AgText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { paddingTop: 8, paddingBottom: 48, gap: 16 },
  flex: { flex: 1 },
  ink: { color: C.ink },
  muted: { color: C.muted },
  pressed: { opacity: 0.72 },
  topRow: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  brandIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: C.greenBg,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: { color: C.amber, letterSpacing: 0.8, textTransform: "uppercase" },
  safetyCard: {
    minHeight: 58,
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    padding: 15,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#E8CB83",
    backgroundColor: C.amberBg,
  },
  safetyCopy: { color: C.ink, flex: 1 },
  stateCard: {
    minHeight: 300,
    padding: 24,
    gap: 14,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  errorIcon: {
    width: 82,
    height: 82,
    borderRadius: 28,
    backgroundColor: C.amberBg,
    alignItems: "center",
    justifyContent: "center",
  },
  summaryCard: {
    padding: 20,
    gap: 16,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
  },
  summaryTop: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  alertIcon: {
    width: 58,
    height: 58,
    borderRadius: 19,
    backgroundColor: C.amberBg,
    alignItems: "center",
    justifyContent: "center",
  },
  divider: { height: 1, backgroundColor: C.border },
  detailRow: { flexDirection: "row", alignItems: "center", gap: 13 },
  guidanceCard: {
    padding: 18,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "#BFD4BE",
    backgroundColor: "#EEF5E9",
    flexDirection: "row",
    gap: 13,
  },
  guidanceIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  verificationCard: {
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E8CB83",
    backgroundColor: C.amberBg,
    flexDirection: "row",
    gap: 12,
  },
  verificationTitle: { color: "#745B22" },
});
