import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { StyleSheet, View } from 'react-native';
import { InfoList } from '../components/InfoList';
import { ConfidenceMeter } from '../components/ConfidenceMeter';

jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/hooks/useAppTheme', () => ({ useAppTheme: () => ({ colors: {
  primary: '#18723a', surface: '#222222', border: '#444444',
  success: '#18723a', warning: '#a65a00', danger: '#b02020',
} }) }));
jest.mock('@/components/ui', () => {
  const { Text, View } = require('react-native');
  return { AgText: Text, AgCard: View };
});

describe('saved report native layout without utility styles', () => {
  it('keeps bullet markers beside wrapping text', async () => {
    let tree!: TestRenderer.ReactTestRenderer;
    await act(async () => { tree = TestRenderer.create(<InfoList icon={View as any} title="Symptoms" items={['Leaf spots']} />); });
    const bullet = tree.root.findByProps({ children: '•' });
    const row = bullet.parent!;
    expect(StyleSheet.flatten(row.props.style).flexDirection).toBe('row');
    expect(StyleSheet.flatten(tree.root.findByProps({ children: 'Leaf spots' }).props.style).flex).toBe(1);
    await act(async () => tree.unmount());
  });
  it.each([null, 0, 77, 100])('renders confidence %s without inventing a missing score', async value => {
    let tree!: TestRenderer.ReactTestRenderer;
    await act(async () => { tree = TestRenderer.create(<ConfidenceMeter value={value} />); });
    expect(tree.root.findByProps({ children: value === null ? 'disease.confidenceUnavailable' : `${value}%` })).toBeTruthy();
    const bar = tree.root.findAllByType(View).find(node => StyleSheet.flatten(node.props.style)?.height === 8);
    expect(bar).toBeTruthy();
    await act(async () => tree.unmount());
  });
});
