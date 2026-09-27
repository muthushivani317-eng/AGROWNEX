import { type Href, useRouter } from "expo-router";
import {
  Activity,
  AlertTriangle,
  Bell,
  BookOpen,
  Bug,
  CalendarDays,
  ClipboardCheck,
  ChevronRight,
  CloudSun,
  FlaskConical,
  History,
  Landmark,
  Layers,
  Tractor,
  Leaf,
  LineChart,
  type LucideIcon,
  MessageCircle,
  MessagesSquare,
  Plus,
  Recycle,
  ShoppingBasket,
  Satellite,
  Sprout,
  Wheat,
  TrendingUp,
  Users,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, TouchableOpacity, View } from "react-native";

import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { internalTestFlags } from "@/config/internalTestFlags";
import { organicFeatureEnabled } from "@/features/organic/featureFlag";

import { HOME_FEATURE_ROUTES, type HomeFeatureKey } from "../routes";

export interface QuickAction {
  key: HomeFeatureKey;
  labelKey: string;
  subtitleKey: string;
  icon: LucideIcon;
}

/** The existing, authoritative Home feature order and visibility list. */
export const QUICK_ACTIONS: QuickAction[] = [
  {
    key: "actionVerification",
    labelKey: "actionVerification.title",
    subtitleKey: "home.actionVerificationDescription",
    icon: ClipboardCheck,
  },
  {
    key: "ai",
    labelKey: "home.actionAI",
    subtitleKey: "home.actionAIDescription",
    icon: MessageCircle,
  },
  {
    key: "disease",
    labelKey: "home.actionDisease",
    subtitleKey: "home.actionDiseaseDescription",
    icon: Bug,
  },
  {
    key: "diseaseRisk",
    labelKey: "home.actionDiseaseRisk",
    subtitleKey: "home.actionDiseaseRiskDescription",
    icon: AlertTriangle,
  },
  {
    key: "addFarm",
    labelKey: "home.actionAddFarm",
    subtitleKey: "home.actionAddFarmDescription",
    icon: Plus,
  },
  {
    key: "calendar",
    labelKey: "home.actionCalendar",
    subtitleKey: "home.actionCalendarDescription",
    icon: CalendarDays,
  },
  {
    key: "growth",
    labelKey: "home.actionGrowth",
    subtitleKey: "home.actionGrowthDescription",
    icon: LineChart,
  },
  {
    key: "harvestReadiness",
    labelKey: "harvestReadiness.title",
    subtitleKey: "home.actionHarvestReadinessDescription",
    icon: Wheat,
  },
  {
    key: "market",
    labelKey: "home.actionMarket",
    subtitleKey: "home.actionMarketDescription",
    icon: TrendingUp,
  },
  {
    key: "schemes",
    labelKey: "home.actionSchemes",
    subtitleKey: "home.actionSchemesDescription",
    icon: Landmark,
  },
  {
    key: "sell",
    labelKey: "home.actionSell",
    subtitleKey: "home.actionSellDescription",
    icon: Sprout,
  },
  {
    key: "soil",
    labelKey: "home.actionSoil",
    subtitleKey: "home.actionSoilDescription",
    icon: Layers,
  },
  {
    key: "weather",
    labelKey: "weather.title",
    subtitleKey: "home.actionWeatherDescription",
    icon: CloudSun,
  },
  {
    key: "satellite",
    labelKey: "home.actionSatellite",
    subtitleKey: "home.actionSatelliteDescription",
    icon: Satellite,
  },
  {
    key: "notifications",
    labelKey: "notifications.title",
    subtitleKey: "home.actionNotificationsDescription",
    icon: Bell,
  },
  {
    key: "plantIdentifier",
    labelKey: "home.actionPlantIdentifier",
    subtitleKey: "home.actionPlantIdentifierDescription",
    icon: Leaf,
  },
  {
    key: "nutrient",
    labelKey: "home.actionNutrient",
    subtitleKey: "home.actionNutrientDescription",
    icon: FlaskConical,
  },
  {
    key: "lcc",
    labelKey: "home.actionLcc",
    subtitleKey: "home.actionLccDescription",
    icon: Leaf,
  },
  {
    key: "inputs",
    labelKey: "home.actionInputs",
    subtitleKey: "home.actionInputsDescription",
    icon: ShoppingBasket,
  },
  {
    // Real, working screens + backend (features/intelligence) with no Home
    // entry anywhere in the app -- a missed line, not a deliberate hold-back
    // (2026-08 pre-release audit).
    key: "intelligence",
    labelKey: "intelligence.title",
    subtitleKey: "home.actionIntelligenceDescription",
    icon: Activity,
  },
  {
    // Same as intelligence above: real, working screens + backend
    // (features/memory), just never linked from Home.
    key: "memory",
    labelKey: "memory.title",
    subtitleKey: "home.actionMemoryDescription",
    icon: History,
  },
  {
    // Complete, release-ready offline crop field guide (5 articles, no AI
    // involved) -- previously gated behind the internal-testing flag along
    // with genuinely unfinished features. Unhidden per explicit product
    // decision, 2026-08 pre-release audit follow-up.
    key: "knowledge",
    labelKey: "home.actionOfflineKnowledge",
    subtitleKey: "home.actionOfflineKnowledgeDescription",
    icon: BookOpen,
  },
  // Real, working screens + backend (features/organic: profile, plan,
  // input library, logbook) already live in production behind
  // EXPO_PUBLIC_AGROWAI_ORGANIC_ENABLED, just never linked from Home
  // (2026-09-23 organic blueprint audit). Same gate the screens already
  // enforce, so this card and the routes it opens fail closed together.
  ...(organicFeatureEnabled
    ? [
        {
          key: "organic" as const,
          labelKey: "home.actionOrganic",
          subtitleKey: "home.actionOrganicDescription",
          icon: Recycle,
        },
      ]
    : []),
  ...(internalTestFlags.internalFeatureTesting
    ? [
        {
          key: "cropRecommendation" as const,
          labelKey: "home.actionCropRecommendation",
          subtitleKey: "home.actionCropRecommendationDescription",
          icon: Sprout,
        },
      ]
    : []),
  ...(internalTestFlags.internalFeatureTesting
    ? [
        {
          key: "equipment" as const,
          labelKey: "home.actionEquipment",
          subtitleKey: "home.actionEquipmentDescription",
          icon: Tractor,
        },
      ]
    : []),
  ...(internalTestFlags.internalFeatureTesting
    ? [
        {
          key: "community" as const,
          labelKey: "home.actionCommunity",
          subtitleKey: "home.actionCommunityDescription",
          icon: MessagesSquare,
        },
      ]
    : []),
  // Gated the same way as cropRecommendation/equipment/community above: the
  // production expert roster isn't populated/verified yet, so this isn't
  // ready for real farmers (2026-08 pre-release audit). Was previously
  // unconditionally visible -- a miss, not a deliberate decision.
  ...(internalTestFlags.internalFeatureTesting
    ? [
        {
          key: "experts" as const,
          labelKey: "home.actionExperts",
          subtitleKey: "home.actionExpertsDescription",
          icon: Users,
        },
      ]
    : []),
];

export function buildQuickActionRows(
  actions: QuickAction[],
  columns = 2,
): QuickAction[][] {
  const rows: QuickAction[][] = [];
  for (let index = 0; index < actions.length; index += columns) {
    rows.push(actions.slice(index, index + columns));
  }
  return rows;
}

// Ordered by how often a farmer uses each tool in day-to-day work:
// daily checks first, seasonal / one-time tools last (2026-09-27).
const FEATURED_ACTION_ORDER: HomeFeatureKey[] = [
  // First: every other tool needs a farm
  "addFarm",
  // Daily
  "weather",
  "disease",
  "ai",
  "market",
  "calendar",
  // Weekly
  "growth",
  "nutrient",
  "organic",
  "diseaseRisk",
  "sell",
  "notifications",
  // Monthly / seasonal
  "soil",
  "satellite",
  "lcc",
  "schemes",
  "inputs",
  "harvestReadiness",
  // Occasional
  "plantIdentifier",
  "knowledge",
  "intelligence",
  "memory",
  "actionVerification",
];

export function homeDisplayOrder(actions: QuickAction[]): QuickAction[] {
  const featured = FEATURED_ACTION_ORDER.flatMap((key) =>
    actions.filter((action) => action.key === key),
  );
  const remaining = actions.filter(
    (action) => !FEATURED_ACTION_ORDER.includes(action.key),
  );
  return [...featured, ...remaining];
}

function FeatureCard({ action }: { action: QuickAction }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const Icon = action.icon;

  return (
    <TouchableOpacity
      testID={`quick-action-${action.key}`}
      onPress={() => router.push(HOME_FEATURE_ROUTES[action.key] as Href)}
      accessibilityRole="button"
      accessibilityLabel={t(action.labelKey)}
      accessibilityHint={t(action.subtitleKey)}
      activeOpacity={0.72}
      style={[
        styles.card,
        {
          backgroundColor: "#FFFDF8",
          // Bumped from 33% to 50% opacity -- the previous border was nearly
          // invisible against the dark theme's card/background colors, which
          // made the whole grid read as a loose, unstructured list rather
          // than a set of distinct tappable cards.
          borderColor: "#DED9CA",
        },
      ]}
    >
      <View style={styles.iconBlock}>
        <Icon size={27} color="#165B33" strokeWidth={1.8} />
      </View>
      <View style={styles.cardCopy}>
        <AgText
          variant="bodyLarge"
          weight="semibold"
          style={styles.title}
          numberOfLines={2}
        >
          {t(action.labelKey)}
        </AgText>
        <AgText
          variant="bodySmall"
          style={styles.cardSubtitle}
          numberOfLines={3}
        >
          {t(action.subtitleKey)}
        </AgText>
      </View>
      <View style={styles.chevronBlock}>
        <ChevronRight size={22} color={colors.primary} />
      </View>
    </TouchableOpacity>
  );
}

function FeatureGrid({ actions }: { actions: QuickAction[] }) {
  const rows = buildQuickActionRows(actions, 1);

  return (
    <View
      testID="quick-access-grid"
      accessibilityLabel="quick-access-grid-1-column"
      style={styles.grid}
    >
      {rows.map((row, rowIndex) => (
        <View
          key={row[0].key}
          testID={`quick-access-row-${rowIndex}`}
          style={styles.row}
        >
          {row.map((action) => (
            <FeatureCard key={action.key} action={action} />
          ))}
        </View>
      ))}
    </View>
  );
}

/** Existing Home quick-access section, presented as one full-width tool per row. */
export function QuickActions() {
  const { t } = useTranslation();
  const actions = homeDisplayOrder(QUICK_ACTIONS);
  return (
    <View style={styles.section}>
      <AgText variant="headingM" weight="bold" style={styles.sectionTitle}>
        {t("home.quickAccess")}
      </AgText>
      <AgText variant="body" style={styles.sectionSubtitle}>
        {t("home.quickAccessSubtitle")}
      </AgText>
      <FeatureGrid actions={actions} />
    </View>
  );
}

const styles = StyleSheet.create({
  section: { width: "100%" },
  sectionTitle: { color: "#173B2B" },
  sectionSubtitle: { marginTop: 3, marginBottom: 12, color: "#58685F" },
  grid: { width: "100%", rowGap: 9 },
  row: {
    width: "100%",
    alignItems: "stretch",
  },
  card: {
    width: "100%",
    minWidth: 0,
    overflow: "hidden",
    minHeight: 92,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 13,
    flexDirection: "row",
    alignItems: "center",
    columnGap: 12,
    // Subtle depth so each card reads as a distinct tappable surface instead
    // of blending into the page background (the flat card + 33%-opacity
    // border was nearly invisible in the dark theme).
    elevation: 1,
    shadowColor: "#000000",
    shadowOpacity: 0.07,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
  },
  iconBlock: {
    width: 48,
    height: 48,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EEF6EC",
  },
  cardCopy: { flex: 1, minWidth: 0 },
  chevronBlock: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: "auto",
    flexShrink: 0,
    backgroundColor: "#EEF6EC",
  },
  title: { minWidth: 0, lineHeight: 22, color: "#173B2B" },
  cardSubtitle: { marginTop: 4, lineHeight: 18, color: "#58685F" },
});
