import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';

import { SOIL_TYPES } from '@/features/farm/constants';

const mockT = (key: string) => key;
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: mockT }) }));
jest.mock('@/hooks/useLanguage', () => ({
  useLanguage: () => ({ language: 'ta', isTamil: true }),
}));

import {
  SoilTypeSelector,
  filterSoilTypes,
  type SoilTypeOption,
} from '../SoilTypeSelector';

const options: SoilTypeOption[] = [
  { value: 'alluvial', label: 'வண்டல்', alternateLabel: 'Alluvial' },
  { value: 'black', label: 'கருப்பு', alternateLabel: 'Black' },
];

describe('shared SoilTypeSelector', () => {
  it('keeps the canonical farm soil IDs unchanged and in one source', () => {
    expect(SOIL_TYPES.map((soil) => soil.value)).toEqual([
      'alluvial', 'black', 'red', 'laterite', 'sandy', 'clay', 'loamy', 'silt',
    ]);
  });

  it('searches case-insensitively across localized names with whitespace normalization', () => {
    expect(filterSoilTypes(options, '  ALLUVIAL  ')).toEqual([options[0]]);
    expect(filterSoilTypes(options, 'கருப்பு')).toEqual([options[1]]);
  });

  it('returns the canonical selected value, exposes selected state, and closes', () => {
    const onSelect = jest.fn();
    const onClose = jest.fn();
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(
        <SoilTypeSelector
          visible
          options={options}
          selectedValue="black"
          onSelect={onSelect}
          onClose={onClose}
        />,
      );
    });

    expect(tree.root.findByProps({ testID: 'soil-option-black' }).props.accessibilityState)
      .toEqual({ selected: true });
    act(() => { tree.root.findByProps({ testID: 'soil-option-alluvial' }).props.onPress(); });
    expect(onSelect).toHaveBeenCalledWith('alluvial');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes without changing the current selection', () => {
    const onSelect = jest.fn();
    const onClose = jest.fn();
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(
        <SoilTypeSelector
          visible
          options={options}
          selectedValue="black"
          onSelect={onSelect}
          onClose={onClose}
        />,
      );
    });
    act(() => { tree.root.findByProps({ testID: 'soil-selector-close' }).props.onPress(); });
    expect(onSelect).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
