import React, { useState } from 'react';
import { TextInput } from 'react-native';

const TestRenderer = require('react-test-renderer');

import { AgOtpInput } from '../AgOtpInput';

function ControlledOtp({ error = false }: { error?: boolean }) {
  const [value, setValue] = useState('');
  return <AgOtpInput value={value} onChange={setValue} error={error} />;
}

describe('AgOtpInput Android native input contract', () => {
  let focus: jest.Mock;
  let isFocused: jest.Mock;
  let tree: any;

  beforeEach(() => {
    focus = jest.fn();
    isFocused = jest.fn(() => true);
  });

  afterEach(() => {
    if (tree) {
      TestRenderer.act(() => tree.unmount());
      tree = undefined;
    }
    jest.useRealTimers();
  });

  const render = (element: React.ReactElement = <ControlledOtp />) => {
    TestRenderer.act(() => {
      tree = TestRenderer.create(element, {
        createNodeMock: (node: { props?: { testID?: string } }) =>
          node.props?.testID === 'otp-native-input' ? { focus, isFocused } : {},
      });
    });
    return tree.root;
  };

  it('uses an editable, non-zero, numeric native TextInput that can open the IME', () => {
    const root = render();
    const input = root.findByType(TextInput);

    expect(input.props.editable).toBe(true);
    expect(input.props.showSoftInputOnFocus).toBe(true);
    expect(input.props.keyboardType).toBe('number-pad');
    expect(input.props.inputMode).toBe('numeric');
    expect(input.props.maxLength).toBe(6);
    expect(input.props.textContentType).toBe('oneTimeCode');
    expect(input.props.autoComplete).toBe('sms-otp');
    expect(input.props.style).toEqual(
      expect.objectContaining({
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 60,
        zIndex: 2,
      }),
    );
    expect(input.props.style.color).toBe('transparent');
    expect(input.props.caretHidden).toBe(true);
    expect(input.props.style).not.toEqual(expect.objectContaining({ opacity: 0 }));
  });

  it('exposes a tap handler across the OTP row', () => {
    const root = render();
    const container = root.findByProps({ testID: 'otp-input-container' });

    expect(container.props.onPress).toEqual(expect.any(Function));
    expect(() => TestRenderer.act(() => container.props.onPress())).not.toThrow();
  });

  it('projects six pasted digits into the six boxes', () => {
    const root = render();
    let input = root.findByType(TextInput);

    TestRenderer.act(() => input.props.onChangeText('123456'));
    input = root.findByType(TextInput);

    expect(input.props.value).toBe('123456');
    for (let index = 0; index < 6; index += 1) {
      const cell = root.findByProps({ testID: `otp-cell-${index}` });
      expect(cell.findByProps({ children: '•' })).toBeTruthy();
    }
    expect(root.findAllByProps({ children: '123456' })).toHaveLength(0);
  });

  it('keeps OTP digits out of visual accessibility nodes and secures the native input', () => {
    const root = render();
    let input = root.findByType(TextInput);

    TestRenderer.act(() => input.props.onChangeText('123456'));
    input = root.findByType(TextInput);
    const visualCells = root.findByProps({ testID: 'otp-visual-cells' });

    expect(input.props.secureTextEntry).toBe(true);
    expect(visualCells.props.accessibilityElementsHidden).toBe(true);
    expect(visualCells.props.importantForAccessibility).toBe('no-hide-descendants');
    for (const digit of '123456') {
      expect(visualCells.findAllByProps({ children: digit })).toHaveLength(0);
    }
  });

  it('rejects non-digits, enforces six digits, and accepts full-code paste', () => {
    const root = render();
    let input = root.findByType(TextInput);

    TestRenderer.act(() => input.props.onChangeText(' 1a2-345678 '));
    input = root.findByType(TextInput);

    expect(input.props.value).toBe('123456');
  });

  it('lets the native text change perform one correct backspace deletion', () => {
    const root = render();
    let input = root.findByType(TextInput);
    TestRenderer.act(() => input.props.onChangeText('123'));
    input = root.findByType(TextInput);

    TestRenderer.act(() => input.props.onChangeText('12'));
    expect(root.findByType(TextInput).props.value).toBe('12');
    expect(root.findByType(TextInput).props.onKeyPress).toBeUndefined();
  });

  it('keeps the input editable after a verification error', () => {
    const root = render(<ControlledOtp error={false} />);

    TestRenderer.act(() => tree.update(<ControlledOtp error />));

    expect(root.findByType(TextInput).props.editable).toBe(true);
  });

  it('does not log OTP digits', () => {
    const log = jest.spyOn(console, 'log').mockImplementation(() => {});
    const error = jest.spyOn(console, 'error').mockImplementation(() => {});
    const root = render();

    TestRenderer.act(() => root.findByType(TextInput).props.onChangeText('654321'));

    expect(log).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
    log.mockRestore();
    error.mockRestore();
  });
});
