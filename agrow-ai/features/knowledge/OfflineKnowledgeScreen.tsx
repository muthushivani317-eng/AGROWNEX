import { useState } from "react";
import { Alert, Linking, StyleSheet, View } from "react-native";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ShieldCheck,
  WifiOff,
} from "lucide-react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";

import { AgPressable, AgScreen, AgText } from "@/components/ui";

import { OFFLINE_KNOWLEDGE, type OfflineKnowledgeArticle } from "./knowledge";
import { ORGANIC_INPUTS_GUIDE, type OrganicRecipeText } from "./organicInputsGuide";

/** Open an online reference without turning a connectivity failure into an unhandled rejection. */
export async function openOfficialKnowledgeSource(url: string): Promise<boolean> {
  try {
    if (!(await Linking.canOpenURL(url))) return false;
    await Linking.openURL(url);
    return true;
  } catch {
    return false;
  }
}

const UI = {
  background: "#FBF7EA",
  surface: "#FFFDF7",
  green: "#17633B",
  greenStrong: "#124B30",
  greenSoft: "#E8F3E5",
  text: "#173F30",
  muted: "#4F6057",
  border: "#D8D2C2",
  amber: "#875400",
  amberSoft: "#FFF4D8",
  amberBorder: "#E5C77A",
} as const;

export function OfflineKnowledgeScreen() {
  const { t, i18n } = useTranslation();
  const [recipeLanguage, setRecipeLanguage] = useState<"en" | "ta" | null>(null);
  const tamil = (recipeLanguage ?? i18n.resolvedLanguage ?? i18n.language).startsWith("ta");
  const articles: Array<OfflineKnowledgeArticle & { content?: OrganicRecipeText }> = [
    ...OFFLINE_KNOWLEDGE,
    ...ORGANIC_INPUTS_GUIDE.map((recipe) => ({
      id: `organic-${recipe.id}`,
      titleKey: "", summaryKey: "", stepsKey: "",
      sourceTitle: "agrowai-organic-inputs-guide.docx",
      sourceUrl: "",
      content: tamil ? recipe.ta : recipe.en,
    })),
  ];
  const router = useRouter();
  const [expanded, setExpanded] = useState<string | null>(
    OFFLINE_KNOWLEDGE[0].id,
  );
  const openSource = async (url: string) => {
    if (await openOfficialKnowledgeSource(url)) return;
    Alert.alert(
      t("offlineKnowledge.sourceUnavailableTitle"),
      t("offlineKnowledge.sourceUnavailableMessage"),
    );
  };

  return (
    <AgScreen
      scroll
      backgroundColor={UI.background}
      contentContainerStyle={styles.content}
    >
      <View style={styles.topBar}>
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          hitSlop={8}
          style={styles.iconButton}
        >
          <ArrowLeft size={26} color={UI.greenStrong} strokeWidth={2.2} />
        </AgPressable>
        <View style={styles.offlinePill}>
          <WifiOff size={16} color={UI.green} />
          <AgText style={styles.offlinePillText} weight="semibold">
            {t("offlineKnowledge.offlineReady")}
          </AgText>
        </View>
      </View>

      <View style={styles.hero}>
        <View style={styles.heroIcon}>
          <BookOpen size={34} color={UI.green} strokeWidth={2} />
        </View>
        <View style={styles.heroCopy}>
          <AgText variant="headingL" weight="bold" style={styles.title}>
            {t("offlineKnowledge.title")}
          </AgText>
          <AgText style={styles.intro}>{t("offlineKnowledge.intro")}</AgText>
        </View>
      </View>

      <View style={styles.safetyCard}>
        <View style={styles.safetyIcon}>
          <ShieldCheck size={24} color={UI.amber} />
        </View>
        <AgText style={styles.safetyText}>
          {t("offlineKnowledge.safety")}
        </AgText>
      </View>

      <View style={styles.sectionHeader}>
        <View style={styles.sectionHeadingCopy}>
          <AgText variant="headingS" weight="bold" style={styles.sectionTitle}>
            {t("offlineKnowledge.title")}
          </AgText>
          <AgText style={styles.sectionMeta}>
            {t("offlineKnowledge.guideCount", {
              count: articles.length,
            })}
          </AgText>
        </View>
        <View style={styles.savedOffline}>
          <CheckCircle2 size={16} color={UI.green} />
          <AgText style={styles.savedOfflineText} weight="semibold">
            {t("offlineKnowledge.savedOffline")}
          </AgText>
        </View>
      </View>

      <View style={styles.safetyCard}>
        <AgText style={styles.safetyText}>
          {tamil
            ? "இயற்கை இடுபொருள் செய்முறைகள் உரிமையாளர் வழங்கிய வழிகாட்டியிலிருந்து பெறப்பட்டவை. இவை உங்கள் பயிருக்கு ஏற்றவை என உறுதிசெய்யப்பட்ட பரிந்துரைகள் அல்ல. தெளிவற்ற அளவு அல்லது செய்முறைக்கு உள்ளூர் வேளாண் அலுவலரிடம் விளக்கம் பெறவும்."
            : "Organic recipes are from the owner's supplied guide, not independently verified crop-specific recommendations. Ask your local agricultural extension officer to clarify incomplete rates or procedures before use."}
        </AgText>
      </View>
      <View style={styles.topBar}>
        <AgText style={styles.sectionTitle}>{tamil ? "இயற்கை செய்முறை மொழி" : "Organic recipe language"}</AgText>
        <AgPressable accessibilityRole="button" accessibilityState={{ selected: tamil }} onPress={() => setRecipeLanguage("ta")} style={styles.offlinePill}>
          <AgText style={styles.offlinePillText}>தமிழ்</AgText>
        </AgPressable>
        <AgPressable accessibilityRole="button" accessibilityState={{ selected: !tamil }} onPress={() => setRecipeLanguage("en")} style={styles.offlinePill}>
          <AgText style={styles.offlinePillText}>English</AgText>
        </AgPressable>
      </View>
      <View style={styles.articleList}>
        {articles.map((article, index) => {
          const open = expanded === article.id;
          return (
            <View
              key={article.id}
              style={[styles.card, open && styles.cardOpen]}
            >
              <AgPressable
                onPress={() => setExpanded(open ? null : article.id)}
                accessibilityRole="button"
                accessibilityState={{ expanded: open }}
                accessibilityLabel={article.content?.title ?? t(article.titleKey)}
                style={styles.articleButton}
              >
                <View
                  style={[
                    styles.articleNumber,
                    open && styles.articleNumberOpen,
                  ]}
                >
                  <AgText
                    style={[
                      styles.articleNumberText,
                      open && styles.articleNumberTextOpen,
                    ]}
                    weight="bold"
                  >
                    {String(index + 1).padStart(2, "0")}
                  </AgText>
                </View>
                <View style={styles.articleCopy}>
                  <AgText
                    variant="headingS"
                    weight="bold"
                    style={styles.articleTitle}
                  >
                    {article.content?.title ?? t(article.titleKey)}
                  </AgText>
                  <AgText style={styles.articleSummary}>
                    {article.content?.summary ?? t(article.summaryKey)}
                  </AgText>
                </View>
                <View style={[styles.chevron, open && styles.chevronOpen]}>
                  {open ? (
                    <ChevronUp size={22} color="#FFFFFF" />
                  ) : (
                    <ChevronDown size={22} color={UI.green} />
                  )}
                </View>
              </AgPressable>

              {open ? (
                <View style={styles.details}>
                  <AgText style={styles.steps}>{article.content?.body ?? t(article.stepsKey)}</AgText>
                  {article.sourceUrl ? (
                  <AgPressable
                    onPress={() => void openSource(article.sourceUrl)}
                    accessibilityRole="link"
                    accessibilityLabel={article.sourceTitle}
                    style={styles.sourceLink}
                  >
                    <ExternalLink size={18} color={UI.green} />
                    <View style={styles.sourceCopy}>
                      <AgText style={styles.sourceLabel} weight="semibold">
                        {t("offlineKnowledge.officialSource")}
                      </AgText>
                      <AgText style={styles.sourceTitle} numberOfLines={2}>
                        {article.sourceTitle}
                      </AgText>
                    </View>
                    <ArrowLeft
                      size={18}
                      color={UI.green}
                      style={styles.sourceArrow}
                    />
                  </AgPressable>
                  ) : (
                    <AgText style={styles.sourceTitle}>
                      {tamil ? "வழங்கப்பட்ட வழிகாட்டி: " : "Supplied guide: "}{article.sourceTitle}
                    </AgText>
                  )}
                </View>
              ) : null}
            </View>
          );
        })}
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 20, paddingBottom: 40 },
  topBar: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: UI.surface,
    borderWidth: 1,
    borderColor: UI.border,
  },
  offlinePill: {
    minHeight: 40,
    maxWidth: "78%",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 13,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: UI.greenSoft,
  },
  offlinePillText: {
    flexShrink: 1,
    color: UI.green,
    fontSize: 12,
    letterSpacing: 0.25,
  },
  hero: { flexDirection: "row", alignItems: "flex-start", gap: 16 },
  heroIcon: {
    width: 64,
    height: 64,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: UI.greenSoft,
    borderWidth: 1,
    borderColor: "#BDD5BB",
  },
  heroCopy: { flex: 1, gap: 8 },
  title: { color: UI.greenStrong, lineHeight: 38 },
  intro: { color: UI.muted, fontSize: 17, lineHeight: 25 },
  safetyCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    padding: 16,
    borderRadius: 20,
    backgroundColor: UI.amberSoft,
    borderWidth: 1,
    borderColor: UI.amberBorder,
  },
  safetyIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFDF7",
  },
  safetyText: { flex: 1, color: "#654B20", fontSize: 15, lineHeight: 23 },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
  },
  sectionHeadingCopy: { flexGrow: 1, flexShrink: 1, minWidth: 180 },
  sectionTitle: { color: UI.text },
  sectionMeta: { color: UI.muted, marginTop: 2 },
  savedOffline: {
    minHeight: 36,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    borderRadius: 18,
    backgroundColor: UI.greenSoft,
  },
  savedOfflineText: { color: UI.green, fontSize: 13 },
  articleList: { gap: 12 },
  card: {
    overflow: "hidden",
    borderRadius: 22,
    backgroundColor: UI.surface,
    borderWidth: 1,
    borderColor: UI.border,
  },
  cardOpen: {
    borderColor: "#94BD95",
    shadowColor: "#173F30",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 2,
  },
  articleButton: {
    minHeight: 88,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: 16,
  },
  articleNumber: {
    width: 44,
    height: 44,
    borderRadius: 14,
    flexShrink: 0,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: UI.greenSoft,
  },
  articleNumberOpen: { backgroundColor: UI.green },
  articleNumberText: { color: UI.green, fontSize: 13 },
  articleNumberTextOpen: { color: "#FFFFFF" },
  articleCopy: { flex: 1, minWidth: 0, gap: 4 },
  articleTitle: { color: UI.text, lineHeight: 24 },
  articleSummary: { color: UI.muted, lineHeight: 21 },
  chevron: {
    width: 40,
    height: 40,
    borderRadius: 20,
    flexShrink: 0,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: UI.greenSoft,
  },
  chevronOpen: { backgroundColor: UI.green },
  details: { gap: 16, paddingHorizontal: 16, paddingBottom: 16 },
  steps: {
    color: UI.text,
    fontSize: 16,
    lineHeight: 25,
    paddingTop: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: UI.border,
  },
  sourceLink: {
    minHeight: 64,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 16,
    backgroundColor: UI.greenSoft,
  },
  sourceCopy: { flex: 1 },
  sourceLabel: { color: UI.green, fontSize: 13 },
  sourceTitle: { color: UI.text, fontSize: 14, lineHeight: 19 },
  sourceArrow: { transform: [{ rotate: "180deg" }] },
});
