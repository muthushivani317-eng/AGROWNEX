import { useRouter } from "expo-router";
import { ArrowRight, ChevronRight, Leaf } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { RefreshControl, ScrollView, StyleSheet, TouchableOpacity, View } from "react-native";

import {
  AgBadge,
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";

import { NutrientBackHeader } from "../components/NutrientBackHeader";
import { STATUS_LABEL_KEY, STATUS_TONE, nutrientLabelKey } from "../constants";
import { useNutrientHistory } from "../hooks/useNutrient";
import { useNutrientSync } from "../hooks/useNutrientSync";
import {
  mayDisplayNutrientFinding,
  safeDisplayStatus,
} from "../services/nutrientPresentation";
import type { NutrientReport } from "../types";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

/** Past nutrient analyses for a farm, with a first-vs-latest comparison. */
export function NutrientHistoryScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  useNutrientSync();

  const { farms, selected, select } = useSelectedFarm();
  const farmId = selected?.id;
  const query = useNutrientHistory(farmId);
  // Do not let cached rows obscure a failed refresh. The error state must be
  // visible so the farmer can retry deliberately.
  const reports = query.isError ? [] : (query.data ?? []);

  return (
    <AgScreen padded={false} backgroundColor={NUTRIENT_UI.canvas}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <NutrientBackHeader title={t("nutrient.historyTitle")} />
        <FarmSelector
          farms={farms}
          selectedId={selected?.id ?? null}
          onSelect={select}
          light
        />

        {query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} className="h-20 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState light onRetry={() => void query.refetch()} />
        ) : reports.length === 0 ? (
          <AgEmptyState
            light
            icon={Leaf}
            title={t("nutrient.historyEmptyTitle")}
            message={t("nutrient.historyEmptyMessage")}
          />
        ) : (
          <>
            {reports.length >= 2 ? <ComparisonCard reports={reports} /> : null}
            {reports.map((report) => (
              <HistoryRow
                key={report.id}
                report={report}
                onPress={() => router.push(`/nutrient/${report.id}`)}
              />
            ))}
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}

function HistoryRow({
  report,
  onPress,
}: {
  report: NutrientReport;
  onPress: () => void;
}) {
  const { t } = useTranslation();
  const a = report.analysis;
  const status = a
    ? safeDisplayStatus(a.resultCode, a.status)
    : "not_confirmed";
  const primary =
    a && mayDisplayNutrientFinding(a.resultCode) ? a.primaryDeficiency : null;

  return (
    <TouchableOpacity
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={t("nutrient.openReport")}
      activeOpacity={0.76}
    >
      <AgCard
        style={styles.surfaceCard}
        className="flex-row items-center gap-3"
      >
        <View className="flex-1 gap-1">
          <View className="flex-row items-center gap-2">
            <AgText variant="body" weight="semibold" style={styles.primaryText}>
              {primary
                ? t(nutrientLabelKey(primary))
                : t("nutrient.status.not_confirmed")}
            </AgText>
            <AgBadge
              light
              label={t(STATUS_LABEL_KEY[status])}
              tone={STATUS_TONE[status]}
            />
          </View>
          <AgText variant="caption" style={styles.mutedText}>
            {(report.captureDate ?? report.createdAt).slice(0, 10)}
            {a
              ? ` · ${t("nutrient.confidence")} ${Math.round(a.confidence)}%`
              : ""}
          </AgText>
        </View>
        <ChevronRight size={18} color={NUTRIENT_UI.muted} />
      </AgCard>
    </TouchableOpacity>
  );
}

function ComparisonCard({ reports }: { reports: NutrientReport[] }) {
  const { t } = useTranslation();
  // History is newest-first.
  const latest = reports[0];
  const first = reports[reports.length - 1];
  const label = (r: NutrientReport) =>
    r.analysis?.primaryDeficiency &&
    mayDisplayNutrientFinding(r.analysis.resultCode)
      ? t(nutrientLabelKey(r.analysis.primaryDeficiency))
      : t("nutrient.status.not_confirmed");

  return (
    <AgCard style={styles.surfaceCard} className="gap-2">
      <AgText variant="label" weight="semibold" style={styles.mutedText}>
        {t("nutrient.comparison")}
      </AgText>
      <View className="flex-row items-center gap-2">
        <View className="flex-1">
          <AgText variant="caption" style={styles.mutedText}>
            {(first.captureDate ?? first.createdAt).slice(0, 10)}
          </AgText>
          <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
            {label(first)}
          </AgText>
        </View>
        <ArrowRight size={16} color={NUTRIENT_UI.muted} />
        <View className="flex-1">
          <AgText variant="caption" style={styles.mutedText}>
            {(latest.captureDate ?? latest.createdAt).slice(0, 10)}
          </AgText>
          <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
            {label(latest)}
          </AgText>
        </View>
      </View>
    </AgCard>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingTop: 2, paddingBottom: 96 },
  surfaceCard: {
    backgroundColor: NUTRIENT_UI.surface,
    borderColor: NUTRIENT_UI.border,
    ...NUTRIENT_SHADOW,
  },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
});
