import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const read = (relative: string) =>
  fs.readFileSync(path.join(root, relative), "utf8");

describe("auth route presentation contract", () => {
  it("wires the actual login, OTP, and profile routes to redesigned screens", () => {
    expect(read("app/(auth)/login.tsx")).toContain("LoginScreen");
    expect(read("app/(auth)/otp.tsx")).toContain("VerifyOtpScreen");
    expect(read("app/(auth)/verify.tsx")).toContain("VerifyOtpScreen");
    expect(read("app/(auth)/complete-profile.tsx")).toContain(
      "CompleteProfileScreen",
    );
  });

  it("uses an Android-safe emblem in the native layer and the branded runtime splash", () => {
    expect(read("app.config.js")).toContain(
      'image: "./assets/images/android-icon-foreground.png"',
    );
    expect(read("app.config.js")).toContain('resizeMode: "contain"');
    expect(read("app.config.js")).not.toContain(
      'image: "./assets/images/agrowai-splash.png"',
    );
    expect(read("app/_layout.tsx")).toContain("<BrandedSplashScreen");
    expect(read("features/auth/screens/SplashScreen.tsx")).toContain(
      'testID="branded-splash-screen"',
    );
  });
});
