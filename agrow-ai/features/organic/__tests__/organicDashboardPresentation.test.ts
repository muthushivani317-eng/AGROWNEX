import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(__dirname, '../../..');
const screen = fs.readFileSync(
  path.join(root, 'features/organic/screens/OrganicDashboardScreen.tsx'),
  'utf8',
);

describe('organic dashboard presentation contract', () => {
  it('renders the AgrowNex field-guide header and illustrated organic hero', () => {
    expect(screen).toContain('accessibilityLabel="AgrowNex"');
    expect(screen).toContain("t('organic.dashboardTitle')");
    expect(screen).toContain("t('organic.dashboardSubtitle')");
    expect(screen).toContain("organic-dashboard-landscape.png");
    expect(screen).toContain('<AuthLanguageSelector');
    expect(screen).toContain('variant="hero"');
  });

  it('preserves every primary organic workflow route', () => {
    expect(screen).toContain('/organic/readiness?farmId=');
    expect(screen).toContain('/organic/conversion-plan?farmId=');
    expect(screen).toContain('/organic/profile?farmId=');
    expect(screen).toContain('/organic/certification?farmId=');
    expect(screen).toContain('/organic/logbook?farmId=');
    expect(screen).toContain('/organic/plan?farmId=');
    expect(screen).toContain("router.push('/organic/inputs'");
  });

  it('keeps live action counts plus loading and error recovery', () => {
    expect(screen).toContain('buildOrganicDashboard(plan.data?.actions ?? [])');
    expect(screen).toContain("t('organic.widgetSummary'");
    expect(screen).toContain('plan.isLoading');
    expect(screen).toContain('plan.isError');
    expect(screen).toContain('plan.refetch()');
  });

  it('uses accessible touch targets and a consistent soft-card radius', () => {
    expect(screen).toContain('minHeight: 48');
    expect(screen).toContain('minHeight: 58');
    expect(screen).toContain('borderRadius: 18');
    expect(screen).toContain('accessibilityRole="button"');
  });

  it('keeps compact layouts readable without transform-only scaling', () => {
    expect(screen).toContain('compact={compact}');
    expect(screen).toContain('styles.featureCardCompact');
    expect(screen).toContain("featureCardCompact: { alignItems: 'stretch', flexDirection: 'column' }");
    expect(screen).not.toContain('transform: [{ scale: 0.82 }]');
    expect(screen).toContain("content: { paddingHorizontal: 16, paddingTop: 14 }");
    expect(screen).toContain('marginBottom: 16');
    expect(screen).toContain("alignSelf: 'stretch'");
  });

  it('uses fixed-light error colors and removes the final action divider', () => {
    expect(screen).toContain('<AgErrorState light');
    expect(screen).toContain('isLast={index === widgets.length - 1}');
    expect(screen).toContain('actionRowLast: { borderBottomWidth: 0 }');
  });

  it('uses direct native touchables for stable horizontal action layouts', () => {
    expect(screen).toContain("import { StyleSheet, TouchableOpacity, useWindowDimensions, View } from 'react-native'");
    expect(screen).toContain('style={[styles.actionRow, isLast && styles.actionRowLast]}');
    expect(screen).toContain('style={styles.primaryAction}');
    expect(screen).toContain('style={styles.libraryAction}');
    expect(screen).not.toContain('<AgPressable');
  });
});
