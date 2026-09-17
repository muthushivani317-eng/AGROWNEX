import fs from 'node:fs';
import path from 'node:path';

const source = fs.readFileSync(
  path.resolve(__dirname, '..', 'screens', 'ProfileScreen.tsx'),
  'utf8',
);

describe('ProfileScreen redesign contract', () => {
  it('keeps the existing edit and account routes', () => {
    expect(source).toMatch(/router\.push\(["']\/profile\/edit["']\)/);
    expect(source).toMatch(/router\.push\(["']\/profile\/account["']\)/);
  });

  it('shows real profile data without fabricating verification or land holding', () => {
    expect(source).toContain('profile.fullName');
    expect(source).toContain('formatIndianPhone(profile.phone)');
    expect(source).toContain('profile.preferredCrops');
    expect(source).not.toContain('Verified');
    expect(source).not.toContain('landHolding');
  });

  it('delegates district editing to the established edit-profile flow', () => {
    expect(source).not.toContain('DistrictSelector');
    expect(source).not.toContain('AgDistrictDropdown');
    expect(source).toMatch(
      /label=\{t\(["']profile\.district["']\)\}[\s\S]*value=\{districtLabel\}[\s\S]*onPress=\{editProfile\}/,
    );
  });

  it('uses the light high-contrast profile system and release-safe touch rows', () => {
    expect(source).toMatch(/const PAGE_BG = ["']#FBF7EA["']/);
    expect(source).toMatch(/const PRIMARY_TEXT = ["']#173B2B["']/);
    expect(source).toContain('<TouchableOpacity');
    expect(source).toMatch(/marginLeft: ["']auto["']/);
    expect(source).not.toContain('style={({ pressed })');
    expect(source).not.toContain("const SCREEN_BG = '#090C0A'");
  });

  it('supports pull-to-refresh without replacing cached data on a refetch failure', () => {
    expect(source).toContain('<RefreshControl');
    expect(source).toContain('refreshing={isRefetching}');
    expect(source).toContain('isRefetchError ?');
    expect(source).toContain('profile.refreshFailedCached');
    expect(source).toMatch(/if \(!profile\)/);
    expect(source).not.toMatch(/if \(isError \|\| !profile\)/);
  });
});
