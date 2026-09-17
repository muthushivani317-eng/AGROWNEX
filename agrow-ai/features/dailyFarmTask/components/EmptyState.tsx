// Empty state for the Today's Farm Task surfaces. Deliberately reassuring,
// not blank -- an empty daily-assistant screen should read as "checked, all
// clear," never as "broken" or "nothing to see here."
import { CircleCheck, RefreshCw } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

export function EmptyState({
  onRefresh,
  refreshing,
}: {
  onRefresh?: () => void;
  refreshing?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  return (
    <View style={styles.container}>
      <CircleCheck size={48} color={colors.primary} />
      <AgText variant="body" weight="semibold" center style={styles.message}>
        {t("dailyTask.emptyState")}
      </AgText>
      {onRefresh ? (
        <Pressable
          onPress={onRefresh}
          accessibilityRole="button"
          style={styles.refreshRow}
        >
          {refreshing ? (
            <ActivityIndicator size="small" color={colors.textMuted} />
          ) : (
            <RefreshCw size={16} color={colors.textMuted} />
          )}
          <AgText variant="bodySmall" style={{ color: colors.textMuted }}>
            {t("dailyTask.emptyRefresh")}
          </AgText>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", justifyContent: "center", paddingVertical: 28, gap: 10 },
  message: { maxWidth: 260 },
  refreshRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4, padding: 6 },
});
