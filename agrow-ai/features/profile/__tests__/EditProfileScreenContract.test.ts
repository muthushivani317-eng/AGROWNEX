import fs from "node:fs";
import path from "node:path";

const source = fs.readFileSync(
  path.resolve(__dirname, "..", "screens", "EditProfileScreen.tsx"),
  "utf8",
);

describe("EditProfileScreen visual contract", () => {
  it("uses the established light, high-contrast profile palette", () => {
    expect(source).toMatch(/const PAGE_BG = ["']#FBF7EA["']/);
    expect(source).toMatch(/const CARD_BG = ["']#FFFDF8["']/);
    expect(source).toMatch(/const PRIMARY_TEXT = ["']#173B2B["']/);
    expect(source).toContain("backgroundColor={PAGE_BG}");
  });

  it("renders explicit accessible choices instead of unstyled text lists", () => {
    expect(source).toContain("function ChoiceChip");
    expect(source).toContain('accessibilityRole="radio"');
    expect(source).toContain('accessibilityRole="checkbox"');
    expect(source).toContain("styles.cropCardSelected");
  });

  it("retains photo, location, validation, and save behavior", () => {
    expect(source).toContain("pickProfileImage");
    expect(source).toContain("autofillAddressFromGPS");
    expect(source).toContain("zodResolver(profileSchema)");
    expect(source).toContain("save.mutate(input");
  });

  it("adapts fields and crop cards for narrow screens", () => {
    expect(source).toContain("const compact = width < 360");
    expect(source).toContain("styles.stackedRow");
    expect(source).toContain("styles.cropCardCompact");
  });
});
