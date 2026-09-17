const React = require('react');
const TestRenderer = require('react-test-renderer');

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock('@/hooks/useLanguage', () => ({
  useLanguage: () => ({ language: 'en', isTamil: false }),
}));
jest.mock('@/hooks/useAppTheme', () => ({
  useAppTheme: () => ({
    colors: {
      primary: '#2E7D32', surface: '#FFFFFF', border: '#E5E7EB', danger: '#E53935',
      text: '#111827', textMuted: '#6B7280', textDisabled: '#9CA3AF', onPrimary: '#FFFFFF',
    },
  }),
}));
jest.mock('lucide-react-native', () => {
  const { View } = require('react-native');
  return new Proxy({}, { get: () => View });
});

import { TAMIL_NADU_DISTRICTS } from '@/constants/locations';
import {
  DistrictSelector,
  filterAndSortDistricts,
  normalizeDistrictSearch,
} from '../DistrictSelector';

describe('DistrictSelector', () => {
  it('normalizes whitespace and filters case-insensitively', () => {
    expect(normalizeDistrictSearch('  COIMBATORE  ')).toBe('coimbatore');
    expect(filterAndSortDistricts(TAMIL_NADU_DISTRICTS, '  coIMbatore ', 'en').map((d) => d.id))
      .toEqual(['coimbatore']);
    expect(filterAndSortDistricts(TAMIL_NADU_DISTRICTS, ' மதுரை ', 'ta').map((d) => d.id))
      .toEqual(['madurai']);
  });

  it('sorts the canonical district source A-Z', () => {
    const result = filterAndSortDistricts(TAMIL_NADU_DISTRICTS, '', 'en');
    expect(result).toHaveLength(TAMIL_NADU_DISTRICTS.length);
    expect(result[0].id).toBe('ariyalur');
    expect(result.at(-1)?.id).toBe('virudhunagar');
  });

  it('closes without changing the selected district', async () => {
    const onClose = jest.fn();
    const onSelect = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(DistrictSelector, {
          visible: true,
          selectedDistrict: 'madurai',
          onClose,
          onSelect,
        }),
      );
    });
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: 'districtSelector.close' }).props.onPress();
    });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSelect).not.toHaveBeenCalled();
    await TestRenderer.act(async () => tree.unmount());
  });

  it('returns the canonical id and closes when a district row is selected', async () => {
    const onClose = jest.fn();
    const onSelect = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(DistrictSelector, { visible: true, onClose, onSelect }),
      );
    });
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: 'Chennai' }).props.onPress();
    });
    expect(onSelect).toHaveBeenCalledWith('chennai');
    expect(onClose).toHaveBeenCalledTimes(1);
    await TestRenderer.act(async () => tree.unmount());
  });

  it('filters live and exposes the no-results state', async () => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(DistrictSelector, { visible: true, onClose: jest.fn(), onSelect: jest.fn() }),
      );
    });
    await TestRenderer.act(async () => {
      tree.root.findByProps({ testID: 'district-search-input' }).props.onChangeText('not a district');
    });
    expect(tree.root.findByProps({ testID: 'district-list' }).props.data).toHaveLength(0);
    expect(tree.root.findByProps({ children: 'districtSelector.noResults' })).toBeTruthy();
    await TestRenderer.act(async () => tree.unmount());
  });
});
