import TestRenderer, { act } from 'react-test-renderer';
import { StyleSheet, Text } from 'react-native';

jest.mock('expo-haptics', () => ({ selectionAsync: jest.fn(() => Promise.resolve()) }));

import { AgPressable } from '../AgPressable';

describe('AgPressable native styles', () => {
  it('flattens style arrays before passing them to the native Pressable', () => {
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(
        <AgPressable testID="pressable" style={[{ flexDirection: 'row' }, { backgroundColor: '#fff' }]}>
          <Text>Row</Text>
        </AgPressable>,
      );
    });

    const pressable = tree.root.findByProps({ testID: 'pressable' });
    expect(StyleSheet.flatten(pressable.props.style)).toMatchObject({
      flexDirection: 'row',
      backgroundColor: '#fff',
    });
  });
});
