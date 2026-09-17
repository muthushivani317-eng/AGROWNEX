import fs from "node:fs";
import path from "node:path";

const screenSource = fs.readFileSync(
  path.resolve(__dirname, "..", "screens", "SchemesScreen.tsx"),
  "utf8",
);
const cardSource = fs.readFileSync(
  path.resolve(__dirname, "..", "components", "SchemeCard.tsx"),
  "utf8",
);
const tabsSource = fs.readFileSync(
  path.resolve(__dirname, "..", "components", "SchemeViewTabs.tsx"),
  "utf8",
);

describe("Government Schemes screen safety contract", () => {
  it("surfaces refresh failures, farm loading and saved-data status", () => {
    expect(screenSource).toContain('data={loading || failed ? [] : active.items}');
    expect(screenSource).toContain('farmQuery.refetch()');
    expect(screenSource).toContain('if (refreshLock.current) return');
    expect(screenSource).toContain('schemes.cachedNotice');
    expect(screenSource).toContain('schemes.saveFailed');
    expect(screenSource).not.toContain('<AgOfflineBanner');
  });
  it("keeps query-backed views, dynamic farm context, and the existing document/detail routes", () => {
    expect(screenSource).toContain("useEligibleSchemes");
    expect(screenSource).toContain("useRecommendedSchemes");
    expect(screenSource).toContain("useBookmarkedSchemes");
    expect(screenSource).toContain("context.district");
    expect(screenSource).toContain("context.crop");
    expect(screenSource).toMatch(
      /router\.push\(["']\/schemes\/my-documents["']\)/,
    );
    expect(cardSource).toContain("router.push(`/schemes/${scheme.id}`)");
  });

  it("uses real bookmark state and only offers official-source wording when a URL exists", () => {
    expect(cardSource).toContain("scheme.bookmarked");
    expect(cardSource).toContain("onToggleBookmark(scheme)");
    expect(cardSource).toContain("scheme.officialUrl");
    expect(cardSource).toMatch(/t\(["']schemes\.verifyOfficialSource["']\)/);
  });

  it("does not present the matching engine as an official eligibility decision", () => {
    expect(cardSource).toMatch(/t\(["']schemes\.potentialMatch["']\)/);
    expect(cardSource).not.toMatch(/t\(["']schemes\.statusEligible["']\)/);
    expect(cardSource).not.toContain("<EligibilityMeter");
  });

  it("retains localized loading, failure, and per-view empty states", () => {
    expect(screenSource).toContain("<SchemesSkeleton");
    expect(screenSource).toContain("<AgErrorState");
    expect(screenSource).toContain("<AgEmptyState");
    expect(screenSource).not.toContain("Testing-only scheme information</");
  });

  it("uses the light design system and small-screen-safe wrapped tabs", () => {
    expect(screenSource).toContain('const SCREEN_BG = "#F7F3E8"');
    expect(cardSource).toContain('backgroundColor: "#FFFFFF"');
    expect(tabsSource).toContain('flexWrap: "wrap"');
    expect(tabsSource).toContain('width: "48%"');
    expect(tabsSource).not.toContain("<ScrollView");
    expect(tabsSource).toContain("<TouchableOpacity");
    expect(tabsSource).toContain("styles.tabSelected");
    expect(screenSource).toContain("<AgErrorState light");
    expect(screenSource).toContain("<AgEmptyState\n                light");
  });
});
