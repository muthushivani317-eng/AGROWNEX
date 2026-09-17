import fs from "node:fs";
import path from "node:path";

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, "../../..", relative), "utf8");

describe("release-visible authentication flow", () => {
  const screen = read("components/ui/AgScreen.tsx");
  const button = read("components/ui/AgButton.tsx");
  const language = read("features/auth/screens/LanguageSelectScreen.tsx");
  const login = read("features/auth/screens/LoginScreen.tsx");
  const otp = read("features/auth/screens/VerifyOtpScreen.tsx");
  const authLayout = read("app/(auth)/_layout.tsx");

  it("does not depend on NativeWind for non-zero root height", () => {
    expect(screen).toContain(
      "style={{ flex: 1, backgroundColor: backgroundColor ?? colors.bg }}",
    );
    expect(screen).toContain("style={{ flex: 1 }}");
  });

  it("keeps the auth controls visible with native release styles", () => {
    const input = read("components/ui/AgInput.tsx");
    const otpInput = read("components/ui/AgOtpInput.tsx");
    const google = read("features/auth/components/SocialAuthButtons.tsx");
    expect(input).toContain("borderWidth: 1.5");
    expect(input).toContain("backgroundColor: fieldBackgroundColor ?? palette.surface");
    expect(input).toContain("backgroundColor: palette.surface");
    expect(input).toMatch(/const palette = light[\s\S]*: colors/);
    expect(otpInput).toContain("styles.cell");
    expect(otpInput).toContain("maxWidth: 52");
    expect(otpInput).toContain("backgroundColor: light ? '#FFFFFF' : colors.surface");
    expect(google).toContain('variant="outline"');
  });

  it("keeps primary actions visible if release class interop fails", () => {
    expect(button).toContain("minHeight: size === 'lg' ? 64");
    expect(button).toContain("backgroundColor:");
  });

  it("registers visible language, login and OTP surfaces", () => {
    expect(language).toContain('testID="language-selection-screen"');
    expect(language).toMatch(/router\.replace\(["']\/\(auth\)\/login["']\)/);
    expect(login).toContain('testID="phone-login-screen"');
    expect(login).toContain('router.push("/(auth)/otp" as Href)');
    expect(otp).toContain('testID="otp-entry-screen"');
    expect(authLayout).toContain('<Stack.Screen name="otp" />');
  });
});
