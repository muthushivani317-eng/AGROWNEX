import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { StyleSheet } from 'react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

import { ChatComposer } from '../components/ChatComposer';

describe('ChatComposer release-safe send control', () => {
  it('shows, enables and submits the right-side send button', () => {
    const onSend = jest.fn();
    let tree!: TestRenderer.ReactTestRenderer;

    act(() => {
      tree = TestRenderer.create(<ChatComposer onSend={onSend} />);
    });

    const input = tree.root.findByProps({ testID: 'ai-composer-input' });
    expect(tree.root.findByProps({ testID: 'ai-send' }).props.disabled).toBe(true);

    act(() => input.props.onChangeText('  How is my crop?  '));

    const enabledSend = tree.root.findByProps({ testID: 'ai-send' });
    expect(enabledSend.props.disabled).toBe(false);
    expect(StyleSheet.flatten(enabledSend.props.style)).toMatchObject({
      width: 48,
      height: 48,
      backgroundColor: '#165B33',
      zIndex: 2,
      elevation: 0,
      shadowOpacity: 0,
    });

    act(() => enabledSend.props.onPress());

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith('How is my crop?');
    expect(tree.root.findByProps({ testID: 'ai-composer-input' }).props.value).toBe('');
  });
});
