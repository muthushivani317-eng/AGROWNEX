import fs from 'node:fs';
import path from 'node:path';

describe('root startup contract', () => {
  const root = fs.readFileSync(path.resolve(__dirname, '../../../app/_layout.tsx'), 'utf8');
  const index = fs.readFileSync(path.resolve(__dirname, '../../../app/index.tsx'), 'utf8');
  const splash = fs.readFileSync(path.resolve(__dirname, '../../auth/screens/SplashScreen.tsx'), 'utf8');

  it('mounts one readiness-owned branded splash and never returns null', () => {
    expect(root).toContain('BrandedSplashScreen');
    expect(root).toMatch(/phase !== ["']READY["'] && phase !== ["']RECOVERABLE_ERROR["']/);
    expect(root).not.toMatch(/return null/);
  });

  it('gives both critical React root containers native flex fallbacks', () => {
    expect(root.match(/style=\{\{ flex: 1/g)?.length).toBeGreaterThanOrEqual(2);
    expect(root).toContain('testID="agrowai-react-root"');
  });

  it('hides the native splash through a once-only guard', () => {
    expect(root).toContain('nativeSplashHidden.current');
    expect(root).toContain('SplashScreen.hideAsync()');
  });

  it('has no competing Redirect in the index route', () => {
    expect(index).not.toContain('Redirect');
    expect(index).toContain('RouteResolvingScreen');
  });

  it('keeps the branded splash readiness-owned without an artificial delay', () => {
    expect(splash).toContain("require('../../../assets/images/android-icon-foreground.png')");
    expect(splash).toContain('resizeMode="contain"');
    expect(splash).toContain('onLoadEnd={onReady}');
    expect(splash).toContain('accessibilityRole="progressbar"');
    expect(splash).not.toContain('durationMs');
    expect(splash).not.toContain('withDelay');
  });
});
