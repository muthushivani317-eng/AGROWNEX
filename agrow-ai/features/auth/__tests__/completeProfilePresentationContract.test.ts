import fs from "node:fs";
import path from "node:path";

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, "../../..", relative), "utf8");

describe("bilingual complete-profile presentation contract", () => {
  const screen = read("features/auth/screens/CompleteProfileScreen.tsx");
  const english = read("localization/locales/en.ts");
  const tamil = read("localization/locales/ta.ts");

  it("preserves the working submission, GPS and dependent location behavior", () => {
    expect(screen).toContain("complete.mutate(data");
    expect(screen).toContain("autofillAddressFromGPS()");
    expect(screen).toMatch(
      /setValue\(["']block["'], ["']["'], \{ shouldDirty: true \}\)/,
    );
    expect(screen).toMatch(
      /setValue\(["']village["'], ["']["'], \{ shouldDirty: true \}\)/,
    );
  });

  it("uses accessible responsive controls without emoji crop icons", () => {
    expect(screen).toContain('accessibilityRole="checkbox"');
    expect(screen).toContain("accessibilityState={{ checked: selected }}");
    expect(screen).toContain("minHeight: 44");
    expect(screen).toContain("minHeight: 58");
    expect(screen).toContain("width < 360");
    expect(screen).toContain("width < 430");
    expect(screen).toContain("styles.locationActionStacked");
    expect(screen).toMatch(/width: ["']100%["'], minHeight: 48/);
    expect(screen).not.toMatch(/[🍌🌾☁️🥜🌶️🫘]/u);
  });

  it("ships matching English and Tamil profile copy and language switching", () => {
    expect(screen).toContain("void setLanguage(nextLanguage)");
    expect(english).toContain('setupEyebrow: "PROFILE SETUP"');
    expect(english).toContain('aboutYou: "About you"');
    expect(tamil).toContain('setupEyebrow: "சுயவிவர அமைப்பு"');
    expect(tamil).toContain('aboutYou: "உங்களைப் பற்றி"');
  });
});
