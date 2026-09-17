import { Info, Satellite, TriangleAlert } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { SEVERITY_TONE } from "../constants";
import type { SatelliteAlert } from "../types";
import { SATELLITE_UI } from "../design";

/** A single satellite alert (localized from its code; deterministic, no fabrication). */
export function SatelliteAlertCard({ alert }: { alert: SatelliteAlert }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon =
    alert.severity === "critical" || alert.severity === "warning"
      ? TriangleAlert
      : alert.severity === "advice"
        ? Satellite
        : Info;
  const iconColor =
    alert.severity === "critical"
      ? colors.danger
      : alert.severity === "warning"
        ? colors.warning
        : colors.primary;

  return (
    <View style={styles.card}>
      <View style={[styles.icon, { backgroundColor: `${iconColor}1A` }]}>
        <Icon size={18} color={iconColor} />
      </View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <AgText variant="body" weight="semibold" style={styles.title}>
            {t(`${alert.code}.title`)}
          </AgText>
          <AgBadge
            light
            label={t(`satellite.severity.${alert.severity}`)}
            tone={SEVERITY_TONE[alert.severity]}
          />
        </View>
        <AgText variant="bodySmall" style={styles.body}>
          {t(`${alert.code}.body`)}
        </AgText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    gap: 12,
    padding: 15,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: SATELLITE_UI.border,
    backgroundColor: SATELLITE_UI.surface,
  },
  icon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  copy: { flex: 1, gap: 6 },
  titleRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  title: { flexGrow: 1, flexShrink: 1, color: SATELLITE_UI.text },
  body: { color: SATELLITE_UI.muted },
});
