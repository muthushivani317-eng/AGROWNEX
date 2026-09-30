import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  FileText,
  Info,
  LandPlot,
  Leaf,
  RefreshCw,
  Sprout,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";

import {
  AgDatePicker,
  AgErrorState,
  AgInput,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";

import { ORGANIC_MODES } from "../constants";
import { useOrganicProfile, useSaveOrganicProfile } from "../hooks/useOrganic";
import { useOrganicSync } from "../hooks/useOrganicSync";
import type { OrganicFarmMode } from "../types";

const C = {
  bg: "#F8FAF5",
  surface: "#FFFFFF",
  ink: "#0A3026",
  text: "#172033",
  muted: "#697286",
  green: "#167438",
  greenSoft: "#ECF7EA",
  border: "#DCE3DF",
  amber: "#D98C08",
  amberSoft: "#FFF3D9",
} as const;

const landscapeImage = require("../../../assets/images/organic-dashboard-landscape.png");
const MODE_ICONS = {
  conventional: Sprout,
  organic_preferred: Leaf,
  transitioning: RefreshCw,
  fully_organic: LandPlot,
} satisfies Record<OrganicFarmMode, typeof Sprout>;

function ModeCard({
  mode,
  selected,
  onPress,
}: {
  mode: OrganicFarmMode;
  selected: boolean;
  onPress: () => void;
}) {
  const { t } = useTranslation();
  const Icon = MODE_ICONS[mode];
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.78}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={t(`organic.mode.${mode}.title`)}
      style={[styles.modeCard, selected && styles.modeCardSelected]}
    >
      <View style={[styles.modeIcon, selected && styles.modeIconSelected]}>
        <Icon size={33} color={C.green} strokeWidth={2.1} />
      </View>
      <View style={styles.modeCopy}>
        <AgText weight="bold" style={styles.modeTitle}>
          {t(`organic.mode.${mode}.title`)}
        </AgText>
        <AgText style={styles.modeDescription}>
          {t(`organic.mode.${mode}.description`)}
        </AgText>
      </View>
      <View style={[styles.radio, selected && styles.radioSelected]}>
        {selected ? <Check size={20} color="#FFFFFF" strokeWidth={3} /> : null}
      </View>
    </TouchableOpacity>
  );
}

export function OrganicProfileScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const query = useOrganicProfile(farmId);
  const save = useSaveOrganicProfile(farmId);
  useOrganicSync();
  const [mode, setMode] = useState<OrganicFarmMode>("organic_preferred");
  const [transitionDate, setTransitionDate] = useState("");
  const [goals, setGoals] = useState("");

  useEffect(() => {
    if (query.data) {
      setMode(query.data.mode);
      setTransitionDate(query.data.transitionStartDate ?? "");
      setGoals(query.data.goals.join(", "));
    }
  }, [query.data]);

  const submit = () =>
    save.mutate(
      {
        mode,
        transitionStartDate: transitionDate.trim() || null,
        goals: goals
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        preferredPractices: [],
      },
      {
        onSuccess: ({ offline }) =>
          Alert.alert(t(offline ? "organic.savedOffline" : "organic.saved")),
      },
    );

  return (
    <AgScreen
      scroll
      keyboardAvoiding
      padded={false}
      backgroundColor={C.bg}
      contentContainerStyle={styles.screen}
    >
      <View style={styles.hero}>
        <Image
          source={landscapeImage}
          contentFit="cover"
          style={styles.heroImage}
        />
        <View style={styles.heroWash} />
        <TouchableOpacity
          onPress={() => router.back()}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={styles.backButton}
        >
          <ArrowLeft size={27} color={C.ink} strokeWidth={2.5} />
        </TouchableOpacity>
        <AgText weight="bold" style={styles.heroTitle}>
          {t("organic.profileTitle")}
        </AgText>
        <AgText style={styles.heroSubtitle}>{t("organic.profileIntro")}</AgText>
      </View>

      <View style={styles.content}>
        {query.isLoading ? (
          <>
            <AgSkeleton style={styles.headingSkeleton} />
            <AgSkeleton style={styles.modeSkeleton} />
            <AgSkeleton style={styles.modeSkeleton} />
            <AgSkeleton style={styles.modeSkeleton} />
          </>
        ) : query.isError ? (
          <View style={styles.errorCard}>
            <AgErrorState
              light
              message={t("organic.loadError")}
              onRetry={() => void query.refetch()}
            />
          </View>
        ) : (
          <>
            <AgText weight="bold" style={styles.sectionTitle}>
              {t("organic.chooseMode")}
            </AgText>
            <View style={styles.modeList} accessibilityRole="radiogroup">
              {ORGANIC_MODES.map((item) => (
                <ModeCard
                  key={item}
                  mode={item}
                  selected={mode === item}
                  onPress={() => setMode(item)}
                />
              ))}
            </View>

            {mode === "transitioning" ? (
              <View style={styles.fieldBlock}>
                <AgDatePicker
                  label={t("organic.transitionDate")}
                  placeholder="YYYY-MM-DD"
                  value={transitionDate}
                  onChange={setTransitionDate}
                  leftAccessory={
                    <CalendarDays size={23} color={C.green} strokeWidth={2.1} />
                  }
                  fieldStyle={styles.field}
                  textStyle={styles.fieldText}
                  labelStyle={styles.fieldLabel}
                />
              </View>
            ) : null}

            <View style={styles.fieldBlock}>
              <AgInput
                light
                label={t("organic.goals")}
                placeholder={t("organic.goalsHint")}
                value={goals}
                onChangeText={setGoals}
                multiline
                leftAccessory={<FileText size={23} color={C.muted} />}
                fieldStyle={styles.goalsField}
                style={styles.goalsInput}
                labelStyle={styles.fieldLabel}
              />
            </View>

            <View style={styles.noticeCard}>
              <View style={styles.noticeIcon}>
                <Info size={24} color={C.amber} strokeWidth={2.4} />
              </View>
              <AgText style={styles.noticeText}>
                {t("organic.certificationNotice")}
              </AgText>
            </View>

            <TouchableOpacity
              onPress={submit}
              activeOpacity={0.82}
              disabled={save.isPending}
              accessibilityRole="button"
              accessibilityState={{ disabled: save.isPending }}
              style={[styles.saveButton, save.isPending && styles.disabled]}
            >
              {save.isPending ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <AgText weight="bold" style={styles.saveText}>
                    {t("common.save")}
                  </AgText>
                  <ArrowRight size={25} color="#FFFFFF" strokeWidth={2.5} />
                </>
              )}
            </TouchableOpacity>
          </>
        )}
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 34 },
  hero: {
    minHeight: 270,
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 24,
    overflow: "hidden",
  },
  heroImage: {
    position: "absolute",
    top: 0,
    right: 0,
    width: "66%",
    height: "100%",
    opacity: 0.88,
  },
  heroWash: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: "rgba(250,252,248,0.65)",
  },
  backButton: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.9)",
    shadowColor: "#173B2B",
    shadowOpacity: 0.09,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  heroTitle: {
    marginTop: 26,
    color: C.ink,
    fontSize: 34,
    lineHeight: 41,
    letterSpacing: -0.8,
  },
  heroSubtitle: {
    maxWidth: 430,
    marginTop: 7,
    color: C.muted,
    fontSize: 16,
    lineHeight: 24,
  },
  content: { marginTop: -20, paddingHorizontal: 16 },
  sectionTitle: { color: C.text, fontSize: 21, lineHeight: 28 },
  modeList: { marginTop: 14, gap: 12 },
  modeCard: {
    minHeight: 112,
    borderRadius: 20,
    borderWidth: 1.25,
    borderColor: C.border,
    backgroundColor: C.surface,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    shadowColor: "#264733",
    shadowOpacity: 0.055,
    shadowRadius: 11,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  modeCardSelected: {
    borderWidth: 2,
    borderColor: C.green,
    backgroundColor: "#F2FAF0",
  },
  modeIcon: {
    width: 68,
    height: 68,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#F4F2E8",
  },
  modeIconSelected: { backgroundColor: "#E1F2DD" },
  modeCopy: { flex: 1, minWidth: 0, marginHorizontal: 14 },
  modeTitle: { color: C.text, fontSize: 18, lineHeight: 24 },
  modeDescription: {
    marginTop: 4,
    color: C.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  radio: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 2,
    borderColor: "#AEB5BA",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  radioSelected: { borderColor: C.green, backgroundColor: C.green },
  fieldBlock: { marginTop: 20 },
  field: {
    minHeight: 64,
    borderRadius: 17,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
  },
  fieldText: { color: C.text, fontSize: 17, lineHeight: 23 },
  fieldLabel: { color: C.text, fontSize: 17, lineHeight: 23 },
  goalsField: {
    minHeight: 104,
    borderRadius: 17,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
    alignItems: "flex-start",
    paddingTop: 15,
  },
  goalsInput: { minHeight: 76, textAlignVertical: "top" },
  noticeCard: {
    minHeight: 88,
    marginTop: 20,
    borderRadius: 18,
    padding: 15,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.amberSoft,
  },
  noticeIcon: {
    width: 43,
    height: 43,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFF8E8",
  },
  noticeText: {
    flex: 1,
    marginLeft: 12,
    color: "#6B4B21",
    fontSize: 14,
    lineHeight: 21,
  },
  saveButton: {
    minHeight: 62,
    marginTop: 20,
    borderRadius: 18,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 13,
    backgroundColor: C.green,
    shadowColor: "#1D6B36",
    shadowOpacity: 0.18,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 5 },
    elevation: 3,
  },
  saveText: { color: "#FFFFFF", fontSize: 19, lineHeight: 25 },
  disabled: { opacity: 0.5 },
  errorCard: {
    minHeight: 300,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: C.border,
    overflow: "hidden",
    backgroundColor: "#FFFFFF",
  },
  headingSkeleton: { width: 180, height: 30, borderRadius: 12 },
  modeSkeleton: { width: "100%", height: 112, marginTop: 12, borderRadius: 20 },
});
