import React from 'react';
import { StyleSheet, TextInput } from 'react-native';

const TestRenderer = require('react-test-renderer');

import { useAppTheme } from '@/hooks/useAppTheme';
import { darkPalette, lightPalette } from '@/theme';

import { AgInput } from '../AgInput';

jest.mock('@/hooks/useAppTheme', () => ({ useAppTheme: jest.fn() }));

describe('AgInput release text visibility', () => {
  const renderInput = () => {
    let tree: any;
    TestRenderer.act(() => {
      tree = TestRenderer.create(<AgInput value="9876543210" onChangeText={jest.fn()} />);
    });
    const input = tree.root.findByType(TextInput);
    const style = StyleSheet.flatten(input.props.style);
    return { tree, input, style };
  };

  beforeEach(() => {
    (useAppTheme as jest.Mock).mockReturnValue({ colors: lightPalette });
  });

  it('uses the light theme surface and contrasting text tokens', () => {
    const { tree, input, style } = renderInput();
    expect(input.props.value).toBe('9876543210');
    expect(style.opacity).toBe(1);
    expect(style.color).toBe(lightPalette.text);
    expect(style.backgroundColor).toBe(lightPalette.surface);
    expect(style.color).not.toBe(style.backgroundColor);
    expect(input.props.placeholderTextColor).toBe(lightPalette.textMuted);
    expect(input.props.cursorColor).toBeTruthy();
    TestRenderer.act(() => tree.unmount());
  });

  it('keeps typed and placeholder text visible in dark mode', () => {
    (useAppTheme as jest.Mock).mockReturnValue({ colors: darkPalette });
    const { tree, input, style } = renderInput();
    expect(style.color).toBe(darkPalette.text);
    expect(style.backgroundColor).toBe(darkPalette.surface);
    expect(style.color).not.toBe(style.backgroundColor);
    expect(input.props.placeholderTextColor).toBe(darkPalette.textMuted);
    expect(input.props.placeholderTextColor).not.toBe(style.backgroundColor);
    TestRenderer.act(() => tree.unmount());
  });
});
