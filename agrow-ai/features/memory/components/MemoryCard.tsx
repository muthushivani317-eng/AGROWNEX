import { useRouter } from "expo-router";
import { ChevronRight, Eye, Sparkles } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgPressable, AgText } from "@/components/ui";
import { relativeTimeKey } from "@/features/home/utils/time";

import {
  OBSERVATION_LABEL_KEY,
  SEASON_LABEL_KEY,
  SOURCE_LABEL_KEY,
} from "../constants";
import type { FarmMemory } from "../types";
import { ImportanceBadge } from "./ImportanceBadge";
import { sourceIcon } from "./sourceMeta";

const C = {
  surface: "#FFFDF7",
  text: "#173F30",
  muted: "#5F6D65",
  green: "#17633B",
  soft: "#E8F3E5",
  border: "#D8D2C2",
} as const;

export function MemoryCard({
  memory,
  onPress,
}: {
  memory: FarmMemory;
  onPress?: () => void;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  const Icon = sourceIcon(memory.sourceModule);
  const ObservationIcon = memory.observation === "observed" ? Eye : Sparkles;
  const rt = relativeTimeKey(memory.occurredAt);
  const go =
    onPress ??
    (() =>
      router.push({ pathname: "/memory/[id]", params: { id: memory.id } }));

  return (
    <AgPressable
      onPress={go}
      accessibilityRole="button"
      accessibilityLabel={t(`${memory.summary}.title`, {
        defaultValue: t("memory.eventFallback"),
      })}
      style={styles.card}
    >
      <View style={styles.topRow}>
        <View style={styles.icon}>
          <Icon size={22} color={C.green} />
        </View>
        <View style={styles.copy}>
          <View style={styles.titleRow}>
            <AgText variant="headingS" weight="bold" style={styles.title}>
              {t(`${memory.summary}.title`, {
                defaultValue: t("memory.eventFallback"),
              })}
            </AgText>
            <ImportanceBadge importance={memory.importance} />
          </View>
          <AgText style={styles.message}>
            {t(`${memory.summary}.message`, {
              defaultValue: "",
              ...(memory.params ?? {}),
            })}
          </AgText>
        </View>
      </View>
      <View style={styles.divider} />
      <View style={styles.metaRow}>
        <View style={styles.metaPill}>
          <ObservationIcon size={14} color={C.green} />
          <AgText style={styles.metaText}>
            {t(OBSERVATION_LABEL_KEY[memory.observation])}
          </AgText>
        </View>
        <View style={styles.metaPill}>
          <AgText style={styles.metaText}>
            {t(SOURCE_LABEL_KEY[memory.sourceModule] ?? memory.sourceModule)}
          </AgText>
        </View>
        {memory.crop ? (
          <View style={styles.metaPill}>
            <AgText style={styles.metaText}>{memory.crop}</AgText>
          </View>
        ) : null}
        {memory.season ? (
          <View style={styles.metaPill}>
            <AgText style={styles.metaText}>
              {t(SEASON_LABEL_KEY[memory.season] ?? memory.season)}
            </AgText>
          </View>
        ) : null}
        {memory.confidence != null ? (
          <View style={styles.metaPill}>
            <AgText style={styles.metaText}>
              {t("memory.confidenceShort", { n: memory.confidence })}
            </AgText>
          </View>
        ) : null}
      </View>
      <View style={styles.footer}>
        <AgText style={styles.time}>{t(rt.key, rt.params)}</AgText>
        <ChevronRight size={20} color={C.green} />
      </View>
    </AgPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 160,
    padding: 16,
    borderRadius: 22,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
  },
  topRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  icon: {
    width: 46,
    height: 46,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.soft,
  },
  copy: { flex: 1, gap: 6 },
  titleRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 8,
  },
  title: { flex: 1, color: C.text, lineHeight: 24 },
  message: { color: C.muted, lineHeight: 22 },
  divider: {
    height: StyleSheet.hairlineWidth,
    marginVertical: 14,
    backgroundColor: C.border,
  },
  metaRow: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  metaPill: {
    minHeight: 30,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 12,
    backgroundColor: C.soft,
  },
  metaText: { color: C.text, fontSize: 12 },
  footer: {
    minHeight: 38,
    marginTop: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  time: { color: C.muted, fontSize: 13 },
});
