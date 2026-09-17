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
      surface: '#FFFFFF', border: '#E5E7EB', danger: '#E53935',
      textMuted: '#6B7280',
    },
  }),
}));
jest.mock('lucide-react-native', () => {
  const { View } = require('react-native');
  return new Proxy({}, { get: () => View });
});

import { COMMON_CROPS } from '@/constants/crops';
import { CropSelector, filterCrops, normalizeCropSearch } from '../CropSelector';

describe('CropSelector', () => {
  it('filters the canonical crop source by English, Tamil, id, case, and whitespace', () => {
    expect(normalizeCropSearch('  PADDY   RICE ')).toBe('paddy rice');
    expect(filterCrops(COMMON_CROPS, '  cOtToN ').map((crop) => crop.id)).toEqual(['cotton']);
    expect(filterCrops(COMMON_CROPS, COMMON_CROPS[0].ta).map((crop) => crop.id)).toEqual(['paddy']);
  });

  it('keeps the canonical ids and does not introduce reference-only crops', () => {
    expect(filterCrops(COMMON_CROPS, '').map((crop) => crop.id)).toEqual(
      COMMON_CROPS.map((crop) => crop.id),
    );
    expect(filterCrops(COMMON_CROPS, 'unsupported reference crop')).toEqual([]);
  });

  it('closes without changing the selected crop', async () => {
    const onClose = jest.fn();
    const onSelect = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(CropSelector, {
          visible: true, selectedCrop: 'cotton', onClose, onSelect,
        }),
      );
    });
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: 'cropSelector.close' }).props.onPress();
    });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSelect).not.toHaveBeenCalled();
    await TestRenderer.act(async () => tree.unmount());
  });

  it('returns a canonical id, closes, and exposes an empty search state', async () => {
    const onClose = jest.fn();
    const onSelect = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(CropSelector, { visible: true, onClose, onSelect }),
      );
    });
    const cotton = COMMON_CROPS.find((crop) => crop.id === 'cotton')!;
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: `${cotton.en}, ${cotton.ta}` }).props.onPress();
    });
    expect(onSelect).toHaveBeenCalledWith('cotton');
    expect(onClose).toHaveBeenCalledTimes(1);

    await TestRenderer.act(async () => {
      tree.root.findByProps({ testID: 'crop-search-input' }).props.onChangeText('not a crop');
    });
    expect(tree.root.findByProps({ testID: 'crop-list' }).props.data).toHaveLength(0);
    expect(tree.root.findByProps({ children: 'cropSelector.noResults' })).toBeTruthy();
    await TestRenderer.act(async () => tree.unmount());
  });
});
