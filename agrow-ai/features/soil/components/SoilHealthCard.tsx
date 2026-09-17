import { CreditCard, Droplet, Leaf } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";

import {
  PARAMETER_LABEL_KEY,
  RATING_LABEL_KEY,
  RATING_TONE,
  SOURCE_LABEL_KEY,
} from "../constants";
import type { SoilAssessment, SoilProfile, SoilSource } from "../types";
import type { SoilIndicatorEvidence } from "../types";
import { evidenceLabelKey } from "../services/soilEvidencePresentation";
import { SOIL_SHADOW, SOIL_UI } from "../design";

interface ParamRow {
  key: string;
  value: number | null;
  unit: string;
  rating: string;
  symbol?: string;
}

/** Soil parameters are displayed exactly as stored; missing values remain explicit. */
export function SoilHealthCard({
  profile,
  assessment,
  evidence = [],
}: {
  profile: SoilProfile | null;
  assessment: SoilAssessment | null;
  evidence?: SoilIndicatorEvidence[];
}) {
  const { t } = useTranslation();
  const { width, fontScale } = useWindowDimensions();
  const compact = width < 370 || fontScale > 1.2;

  const rows: ParamRow[] = [
    {
      key: "ph",
      value: profile?.ph ?? null,
      unit: "",
      rating: assessment?.phClass ?? "unknown",
      symbol: "pH",
    },
    {
      key: "organic_carbon",
      value: profile?.organicCarbon ?? null,
      unit: "%",
      rating: assessment?.organicCarbon ?? "unknown",
    },
    {
      key: "nitrogen",
      value: profile?.nitrogen ?? null,
      unit: "kg/ha",
      rating: assessment?.nitrogen ?? "unknown",
      symbol: "N",
    },
    {
      key: "phosphorus",
      value: profile?.phosphorus ?? null,
      unit: "kg/ha",
      rating: assessment?.phosphorus ?? "unknown",
      symbol: "P",
    },
    {
      key: "potassium",
      value: profile?.potassium ?? null,
      unit: "kg/ha",
      rating: assessment?.potassium ?? "unknown",
      symbol: "K",
    },
    {
      key: "ec_salinity",
      value: profile?.ecSalinity ?? null,
      unit: "dS/m",
      rating: assessment?.salinity ?? "unknown",
    },
  ];

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: SOIL_UI.surface, borderColor: SOIL_UI.border },
      ]}
    >
      <View style={styles.header}>
        <View style={[styles.headerIcon, { backgroundColor: SOIL_UI.greenSoft }]}>
          <CreditCard size={25} color={SOIL_UI.green} />
        </View>
        <AgText variant="headingS" weight="bold" style={[styles.headerTitle, styles.fixedText]}>
          {t("soil.healthCard")}
        </AgText>
        {profile ? (
          <AgBadge
            light
            label={t(
              SOURCE_LABEL_KEY[profile.source as SoilSource] ??
                "soil.sourceSelf",
            )}
            tone="info"
          />
        ) : null}
      </View>

      {rows.map((row, index) => (
        <View
          key={row.key}
          style={[
            styles.row,
            compact && styles.rowCompact,
            index > 0 && { borderTopColor: SOIL_UI.border, borderTopWidth: 1 },
          ]}
        >
          <View
            style={[
              styles.parameterIcon,
              { backgroundColor: SOIL_UI.surfaceSoft, borderColor: SOIL_UI.border },
            ]}
          >
            {row.key === "organic_carbon" ? (
              <Leaf size={25} color={SOIL_UI.green} />
            ) : row.key === "ec_salinity" ? (
              <Droplet size={25} color="#1677A5" />
            ) : (
              <AgText variant="label" weight="bold" style={styles.greenText}>
                {row.symbol}
              </AgText>
            )}
          </View>

          <View style={styles.parameterCopy}>
            <AgText variant="bodyLarge" weight="semibold" style={styles.fixedText}>
              {t(PARAMETER_LABEL_KEY[row.key])}
            </AgText>
            <AgText variant="bodySmall" style={styles.fixedMuted}>
              {t(`soil.${parameterDescriptionKey[row.key]}`)}
            </AgText>
            <AgText variant="caption" style={styles.fixedMuted}>
              {t(
                evidenceLabelKey(
                  evidence.find((item) => item.indicator === row.key),
                  profile?.source as SoilSource | undefined,
                ),
              )}
            </AgText>
          </View>

          <View style={[styles.valueArea, compact && styles.valueAreaCompact]}>
            <View
              style={[styles.valueChip, { backgroundColor: SOIL_UI.surfaceSoft }]}
            >
              <AgText variant="bodySmall" weight="semibold" numberOfLines={1} style={styles.fixedText}>
                {row.value === null
                  ? t("soil.notAvailable")
                  : `${row.value}${row.unit ? ` ${row.unit}` : ""}`}
              </AgText>
            </View>
            {row.rating !== "unknown" ? (
              <AgBadge
                light
                label={t(RATING_LABEL_KEY[row.rating] ?? "soil.ratingUnknown")}
                tone={RATING_TONE[row.rating] ?? "neutral"}
              />
            ) : (
              <AgText variant="body" style={styles.fixedMuted}>
                —
              </AgText>
            )}
          </View>
        </View>
      ))}
    </View>
  );
}

const parameterDescriptionKey: Record<string, string> = {
  ph: "paramPhDescription",
  organic_carbon: "paramOrganicCarbonDescription",
  nitrogen: "paramNitrogenDescription",
  phosphorus: "paramPhosphorusDescription",
  potassium: "paramPotassiumDescription",
  ec_salinity: "paramSalinityDescription",
};

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 24,
    overflow: "hidden",
    ...SOIL_SHADOW,
  },
  header: {
    minHeight: 76,
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  headerTitle: { flex: 1 },
  row: {
    minHeight: 104,
    marginHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  rowCompact: { flexWrap: "wrap", paddingVertical: 14 },
  parameterIcon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  parameterCopy: { flex: 1, gap: 2 },
  valueArea: { alignItems: "flex-end", gap: 5, maxWidth: 128 },
  valueAreaCompact: {
    width: "100%",
    maxWidth: undefined,
    alignItems: "flex-start",
    paddingLeft: 66,
  },
  valueChip: {
    minHeight: 38,
    borderRadius: 16,
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  fixedText: { color: SOIL_UI.text },
  fixedMuted: { color: SOIL_UI.muted },
  greenText: { color: SOIL_UI.green },
});
