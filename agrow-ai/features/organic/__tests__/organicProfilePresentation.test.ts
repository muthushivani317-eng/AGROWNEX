import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const screen = fs.readFileSync(
  path.join(root, "features/organic/screens/OrganicProfileScreen.tsx"),
  "utf8",
);

describe("organic profile presentation contract", () => {
  it("renders the illustrated farm-plan header and all server-supported modes", () => {
    expect(screen).toContain("organic-dashboard-landscape.png");
    expect(screen).toContain("ORGANIC_MODES.map");
    expect(screen).toContain("<ModeCard");
    expect(screen).toContain('t("organic.profileTitle")');
  });

  it("preserves profile persistence, offline feedback, and retry states", () => {
    expect(screen).toContain("useOrganicProfile(farmId)");
    expect(screen).toContain("useSaveOrganicProfile(farmId)");
    expect(screen).toContain("useOrganicSync()");
    expect(screen).toContain(
      'offline ? "organic.savedOffline" : "organic.saved"',
    );
    expect(screen).toContain("query.refetch()");
  });

  it("uses accessible mode selection and native-styled actions", () => {
    expect(screen).toContain('accessibilityRole="radiogroup"');
    expect(screen).toContain('accessibilityRole="radio"');
    expect(screen).toContain('accessibilityRole="button"');
    expect(screen).toContain("<AgDatePicker");
  });
});
