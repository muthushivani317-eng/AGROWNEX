const React = require('react');
const TestRenderer = require('react-test-renderer');

import { ConfigurationErrorScreen } from '../ConfigurationErrorScreen';

describe('ConfigurationErrorScreen', () => {
  it('renders a Tamil-first safe fallback instead of throwing', () => {
    let tree: any;
    expect(() => {
      TestRenderer.act(() => {
        tree = TestRenderer.create(<ConfigurationErrorScreen category="api_url_insecure" />);
      });
    }).not.toThrow();

    expect(tree.root.findByProps({ testID: 'configuration-error-screen' })).toBeTruthy();
    expect(tree.root.findByProps({ testID: 'configuration-error-category' }).props.children).toBe(
      'api_url_insecure',
    );
    const text = tree.root
      .findAllByType('Text')
      .flatMap((node: any) => node.props.children)
      .join(' ');
    expect(text).toContain('configurationError.title');
  });
});
