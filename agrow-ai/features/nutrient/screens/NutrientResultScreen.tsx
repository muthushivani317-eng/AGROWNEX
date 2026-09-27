import { Image } from "expo-image";
import { useRouter } from "expo-router";
import { FlaskConical, UserCog } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";

import {
  AgButton,
  AgCard,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { DeficiencyResultCard } from "../components/DeficiencyResultCard";
import { EvidenceCard } from "../components/EvidenceCard";
import { NutrientBackHeader } from "../components/NutrientBackHeader";
import { NutrientRecommendationCard } from "../components/NutrientRecommendationCard";
import { SymptomList } from "../components/SymptomList";
import { useNutrientReport } from "../hooks/useNutrient";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

/** A full nutrient-analysis report: verdict, symptoms, evidence and generic advice. */
export function NutrientResultScreen({ reportId }: { reportId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const query = useNutrientReport(reportId);

  const report = query.data;

  return (
    <AgScreen padded={false} backgroundColor={NUTRIENT_UI.canvas}>
      <View style={styles.header}>
        <NutrientBackHeader title={t("nutrient.resultHeader")} />
      </View>
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
        {query.isLoading ? (
          <View className="gap-3">
            <AgSkeleton className="h-56 w-full rounded-card" />
            <AgSkeleton className="h-40 w-full rounded-card" />
            <AgSkeleton className="h-28 w-full rounded-card" />
          </View>
        ) : query.isError || !report ? (
          <AgErrorState light onRetry={() => void query.refetch()} />
        ) : (
          <>
            <Image
              source={{ uri: report.imageUrl }}
              style={styles.reportImage}
              contentFit="cover"
            />

            {report.analysis ? (
              <DeficiencyResultCard analysis={report.analysis} />
            ) : null}

            <SymptomList symptoms={report.symptoms} />

            {report.analysis ? (
              <EvidenceCard analysis={report.analysis} />
            ) : null}
            {report.analysis ? (
              <AgCard style={styles.surfaceCard} className="gap-1">
                <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
                  {t(`nutrient.resultCode.${report.analysis.resultCode}`)}
                </AgText>
                <AgText variant="caption" style={styles.mutedText}>
                  {t(
                    `nutrient.confidenceBand.${report.analysis.confidenceBand}`,
                  )}
                </AgText>
                {!report.analysis.expertVerified ? (
                  <AgText variant="caption" style={styles.mutedText}>
                    {t("nutrient.notExpertVerified")}
                  </AgText>
                ) : null}
              </AgCard>
            ) : null}

            {report.recommendations.length > 0 ? (
              <View className="gap-2">
                <AgText variant="label" weight="semibold" style={styles.mutedText}>
                  {t("nutrient.recommendationsTitle")}
                </AgText>
                {report.recommendations.map((rec) => (
                  <NutrientRecommendationCard key={rec.code} rec={rec} diseaseConflict={Boolean(report.analysis?.diseaseConflict)} />
                ))}
              </View>
            ) : null}

            {report.analysis?.needsTest ? (
              <AgButton
                light
                variant="outline"
                title={t("nutrient.goToSoil")}
                leftIcon={<FlaskConical size={18} color={colors.primary} />}
                onPress={() => router.push(`/soil?farmId=${report.farmId}`)}
              />
            ) : null}
            {report.analysis?.needsExpert ? (
              <AgButton
                light
                variant="outline"
                title={t("nutrient.askExpert")}
                leftIcon={<UserCog size={18} color={colors.primary} />}
                onPress={() => router.push("/consultations")}
              />
            ) : null}

            <AgCard style={styles.surfaceCard}>
              <AgText variant="caption" style={styles.mutedText}>
                {t("nutrient.disclaimer")}
              </AgText>
            </AgCard>
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: 20, paddingTop: 2 },
  scroll: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingTop: 8, paddingBottom: 96 },
  reportImage: {
    width: "100%",
    aspectRatio: 1.4,
    borderRadius: 22,
    backgroundColor: NUTRIENT_UI.surfaceSoft,
    ...NUTRIENT_SHADOW,
  },
  surfaceCard: {
    backgroundColor: NUTRIENT_UI.surface,
    borderColor: NUTRIENT_UI.border,
  },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
});
