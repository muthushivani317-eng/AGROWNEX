const React = require('react');
const TestRenderer = require('react-test-renderer');
import { StartupStatusScreen } from '../StartupScreens';
import { SplashScreen } from '@/features/auth/screens/SplashScreen';

describe('visible startup screens', () => {
  it('renders the responsive branded splash with accessible progress', async () => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(React.createElement(SplashScreen));
    });
    const artwork = tree.root.findByProps({ testID: 'branded-splash-artwork' });
    expect(artwork.props.resizeMode).toBe('contain');
    expect(tree.root.findByProps({ testID: 'branded-splash-screen' })).toBeTruthy();
    expect(tree.root.findByProps({ accessibilityRole: 'progressbar' })).toBeTruthy();
    expect(tree.root.findByProps({ children: 'Intelligence for every field' }).props.style.color).toBe('#173B2B');
    expect(tree.root.findByProps({ children: 'Preparing your farm intelligence…' }).props.style.color).toBe('#365445');
  });

  it('never renders null while booting', async () => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(React.createElement(StartupStatusScreen, { phase: 'BOOTING' }));
    });
    expect(tree.root.findByProps({ testID: 'startup-loading-screen' })).toBeTruthy();
    expect(tree.root.findByProps({ testID: 'startup-spinner' })).toBeTruthy();
  });

  it('renders safe retry and reset controls after failure', async () => {
    const retry = jest.fn();
    const reset = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(React.createElement(StartupStatusScreen, {
        phase: 'RECOVERABLE_ERROR', errorCategory: 'database_initialization_failed', onRetry: retry, onReset: reset,
      }));
    });
    tree.root.findByProps({ testID: 'startup-retry' }).props.onPress();
    tree.root.findByProps({ testID: 'startup-safe-reset' }).props.onPress();
    expect(retry).toHaveBeenCalledTimes(1);
    expect(reset).toHaveBeenCalledTimes(1);
    expect(tree.root.findByProps({ testID: 'startup-error-category' }).props.children).toBe('database_initialization_failed');
  });
});
