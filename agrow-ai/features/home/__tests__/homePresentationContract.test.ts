import fs from "node:fs";
import path from "node:path";

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, "../../..", relative), "utf8");

describe("bilingual home presentation contract", () => {
  const home = read("features/home/screens/HomeScreen.tsx");
  const header = read("features/home/components/DashboardHeader.tsx");
  const priority = read("features/home/components/PriorityHeroCard.tsx");
  const actions = read("features/home/components/QuickActions.tsx");
  const farmSelector = read("features/weather/components/FarmSelector.tsx");
  const tabs = read("app/(tabs)/_layout.tsx");

  it("keeps live dashboard modules and refresh behavior wired", () => {
    expect(home).toContain("<PriorityHeroCard />");
    expect(home).toContain("<TodaysFarmCard");
    expect(home).toContain("<TodaysTasks tasks={tasks} />");
    expect(home).toContain("<QuickActions />");
    expect(home).toContain("refreshControl=");
  });

  it("provides bilingual, accessible header controls without emoji decoration", () => {
    expect(header).toContain(
      "void setLanguage(language === 'ta' ? 'en' : 'ta')",
    );
    expect(header).toContain(
      "accessibilityLabel={t('profile.changeLanguage')}",
    );
    expect(header).toContain("<NotificationBell light />");
    expect(header).not.toMatch(/[👋]/u);
  });

  it("uses the approved priority hierarchy and keeps every tool route", () => {
    expect(priority).toContain("backgroundColor: '#165B33'");
    expect(priority).toContain("t('common.viewDetails')");
    expect(actions).toContain("FEATURED_ACTION_ORDER");
    expect(actions).toContain("<FeatureGrid actions={actions} />");
    expect(actions).toContain("HOME_FEATURE_ROUTES[action.key]");
    expect(actions).toContain('accessibilityLabel="quick-access-grid-1-column"');
    expect(actions).toContain("buildQuickActionRows(actions, 1)");
    expect(actions).toContain("minHeight: 92");
    expect(home).toMatch(
      /sectionShell: \{ width: ["']100%["'], alignSelf: ["']stretch["'] \}/,
    );
  });

  it("keeps compact farm identity and home navigation readable on the light dashboard", () => {
    expect(farmSelector).toContain("compactSelectedCopy");
    expect(farmSelector).toContain("lightMutedText");
    expect(header).toContain("style={styles.timeText}");
    expect(tabs).toContain("tabBarActiveTintColor: '#FFFFFF'");
    expect(tabs).toContain("tabBarInactiveTintColor: '#DCEADF'");
  });
});
