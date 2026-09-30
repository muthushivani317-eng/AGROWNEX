import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const screen = fs.readFileSync(
  path.join(root, "features/organic/screens/OrganicLogbookScreen.tsx"),
  "utf8",
);

describe("organic logbook presentation contract", () => {
  it("renders the illustrated field-journal header and complete entry form", () => {
    expect(screen).toContain("organic-dashboard-landscape.png");
    expect(screen).toContain('t("organic.logbookTitle")');
    expect(screen).toContain('t("organic.logbookSubtitle")');
    expect(screen).toContain("PRACTICE_TYPES.map");
    expect(screen).toContain("OUTCOMES.map");
  });

  it("preserves create, evidence upload, validation, and offline feedback", () => {
    expect(screen).toContain("useCreateOrganicPractice(farmId)");
    expect(screen).toContain("useUploadOrganicEvidence(farmId)");
    expect(screen).toContain("quantityUnitRequiredTogether");
    expect(screen).toContain(
      'offline ? "organic.savedOffline" : "organic.practiceSaved"',
    );
  });

  it("keeps loading, retry, empty, and recorded-history states", () => {
    expect(screen).toContain("query.isLoading");
    expect(screen).toContain("query.isError");
    expect(screen).toContain("query.refetch()");
    expect(screen).toContain('t("organic.emptyTitle")');
    expect(screen).toContain("query.data.map");
  });

  it("uses responsive fields and accessible 48px touch targets", () => {
    expect(screen).toContain("useWindowDimensions().width < 390");
    expect(screen).toContain("minHeight: 48");
    expect(screen).toContain('accessibilityRole="radio"');
    expect(screen).toContain('accessibilityRole="button"');
  });

  it("uses fixed responsive tiles for practice types and outcomes", () => {
    expect(screen).toContain('variant="practice"');
    expect(screen).toContain('variant="outcome"');
    expect(screen).toContain("compact={compact}");
    expect(screen).toContain('chipCompact: { width: "48.6%" }');
    expect(screen).toContain("<TouchableOpacity");
  });
});
