import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(__dirname, '../../..');
const read = (relative: string) =>
  fs.readFileSync(path.join(root, relative), 'utf8');

describe('approved redesign route coverage', () => {
  it.each([
    ['app/(auth)/language.tsx', 'LanguageSelectScreen'],
    ['app/(auth)/login.tsx', 'LoginScreen'],
    ['app/(auth)/otp.tsx', 'VerifyOtpScreen'],
    ['app/(auth)/verify.tsx', 'VerifyOtpScreen'],
    ['app/(auth)/complete-profile.tsx', 'CompleteProfileScreen'],
    ['app/(tabs)/index.tsx', 'HomeScreen'],
    ['app/disease/index.tsx', 'DiseaseScreen'],
    ['app/(tabs)/ai.tsx', 'ChatScreen'],
    ['app/calendar/index.tsx', 'CalendarScreen'],
    ['app/growth/index.tsx', 'GrowthMonitorScreen'],
    ['app/schemes/index.tsx', 'SchemesScreen'],
  ])('%s renders %s', (route, screen) => {
    expect(read(route)).toContain(screen);
  });

  it('keeps the disease crop-selection flow inside the redesigned disease screen', () => {
    const screen = read('features/disease/screens/DiseaseScreen.tsx');
    expect(screen).toContain('ENTRY_BG');
    expect(screen).toContain('selectCropAlternative');
    expect(screen).toContain('accessibilityState={{ selected: cropId === crop }}');
  });

  it('never flashes the legacy route-resolving spinner after the branded splash', () => {
    const startup = read('features/startup/StartupScreens.tsx');
    expect(startup).toContain('<SplashScreen />');
    expect(startup).not.toContain("t('startup.openingApp')");
  });

  it('keeps the profile location action visible and accessible', () => {
    const profile = read('features/auth/screens/CompleteProfileScreen.tsx');
    expect(profile).toContain('accessibilityLabel={t("profile.useMyLocation")}');
    // Onboarding v2: GPS autofill is a full-width card on the Location step.
    expect(profile).toContain('style={styles.gpsCard}');
    expect(profile).toContain('onPress={onUseMyLocation}');
  });
});
