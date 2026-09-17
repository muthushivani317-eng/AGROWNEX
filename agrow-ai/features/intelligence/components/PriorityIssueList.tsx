import { AlertTriangle } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { MODULE_LABEL_KEY } from "../constants";
import { INTELLIGENCE_COLORS as C } from "../design";
import type { PriorityIssue } from "../types";

/**
 * The ranked priority issues (most severe first). Each is a generic localization code
 * with the contributing modules — no fabricated diagnosis, no brand advice.
 */
export function PriorityIssueList({ issues }: { issues: PriorityIssue[] }) {
  const { t } = useTranslation();
  if (issues.length === 0) return null;

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <View style={styles.headingIcon}>
          <AlertTriangle size={18} color={C.warning} />
        </View>
        <AgText variant="headingS" weight="bold" style={styles.inkText}>
          {t("intelligence.priorityIssues")}
        </AgText>
      </View>
      {issues.map((issue, index) => {
        const severe = issue.severity === "critical";
        const color = severe ? C.danger : C.warning;
        const soft = severe ? C.dangerSoft : C.warningSoft;
        return (
          <View
            key={`${issue.code}-${index}`}
            style={[styles.issueCard, { borderLeftColor: color }]}
          >
            <View style={styles.issueTop}>
              <AgText
                variant="body"
                weight="bold"
                style={[styles.inkText, styles.flexText]}
              >
                {t(`${issue.code}.title`, {
                  defaultValue: t("intelligence.issueFallback"),
                })}
              </AgText>
              <View style={[styles.severityPill, { backgroundColor: soft }]}>
                <AgText variant="caption" weight="bold" style={{ color }}>
                  {t(`intelligence.severity.${issue.severity}`)}
                </AgText>
              </View>
            </View>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t(`${issue.code}.message`, { defaultValue: "" })}
            </AgText>
            {issue.modules.length > 0 ? (
              <View style={styles.chips}>
                {issue.modules.map((m) => (
                  <View key={m} style={styles.chip}>
                    <AgText
                      variant="caption"
                      weight="semibold"
                      style={styles.primaryText}
                    >
                      {t(MODULE_LABEL_KEY[m] ?? m)}
                    </AgText>
                  </View>
                ))}
              </View>
            ) : null}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: 10 },
  sectionHeader: { flexDirection: "row", alignItems: "center", gap: 10 },
  headingIcon: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: C.goldSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  issueCard: {
    backgroundColor: C.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: C.border,
    borderLeftWidth: 5,
    padding: 16,
    gap: 9,
  },
  issueTop: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  flexText: { flex: 1 },
  severityPill: { borderRadius: 999, paddingHorizontal: 9, paddingVertical: 5 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 2 },
  chip: {
    backgroundColor: C.surfaceSoft,
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  inkText: { color: C.ink },
  mutedText: { color: C.muted },
  primaryText: { color: C.primary },
});
