import fs from "node:fs";
import path from "node:path";

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, "../../..", relative), "utf8");

describe("bilingual login presentation contract", () => {
  const login = read("features/auth/screens/LoginScreen.tsx");
  const hero = read("features/auth/components/AuthHero.tsx");
  const languageSelector = read(
    "features/auth/components/AuthLanguageSelector.tsx",
  );
  const english = read("localization/locales/en.ts");
  const tamil = read("localization/locales/ta.ts");

  it("keeps the Agronex field-gate layout and existing OTP action", () => {
    expect(login).toContain(
      "showWelcome={!keyboardVisible}",
    );
    expect(login).toContain("styles.sproutBadge");
    expect(login).toContain("styles.otpReassurance");
    expect(login).toContain("sendOtp.mutate(phone");
    expect(login).toContain(
      "disabled={!formState.isValid || sendOtp.isPending}",
    );
    expect(login).toContain('Keyboard.addListener("keyboardDidShow"');
    expect(login).toContain('Keyboard.addListener("keyboardDidHide"');
    expect(login).toContain('paddingHorizontal: 18');
    expect(login).not.toContain('marginHorizontal: 20');
  });

  it("provides an accessible 48dp language selector in the hero", () => {
    expect(hero).toContain('<AuthLanguageSelector variant="hero" />');
    expect(languageSelector).toContain('accessibilityRole="tablist"');
    expect(languageSelector).toContain('accessibilityRole="tab"');
    expect(languageSelector).toContain("minHeight: 48");
    expect(languageSelector).toContain("{compact ? 'EN' : 'English'}");
  });

  it("ships complete English and Tamil login copy", () => {
    expect(english).toContain(
      "Simple, trusted farming guidance in your language.",
    );
    expect(english).toContain("Your data is safe with us.");
    expect(tamil).toContain(
      "உங்கள் மொழியில் எளிய, நம்பகமான விவசாய வழிகாட்டுதல்.",
    );
    expect(tamil).toContain("உங்கள் தரவு எங்களிடம் பாதுகாப்பாக உள்ளது.");
  });
});
