import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';

import { IRRIGATION_TYPES } from '@/features/farm/constants';
import { en } from '@/localization/locales/en';
import { ta } from '@/localization/locales/ta';

jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/hooks/useLanguage', () => ({
  useLanguage: () => ({ language: 'ta', isTamil: true }),
}));

import {
  IrrigationTypeSelector,
  filterIrrigationTypes,
  type IrrigationTypeOption,
} from '../IrrigationTypeSelector';

const options: IrrigationTypeOption[] = [
  { value: 'rainfed', label: 'மழை நீர்', alternateLabel: 'Rain-fed', subtitle: 'மழையைச் சார்ந்தது' },
  { value: 'canal', label: 'கால்வாய்', alternateLabel: 'Canal', subtitle: 'கால்வாய் நீர்' },
];

describe('shared IrrigationTypeSelector', () => {
  it('preserves every canonical irrigation value', () => {
    expect(IRRIGATION_TYPES.map((item) => item.value)).toEqual([
      'rainfed', 'canal', 'borewell', 'open_well', 'drip', 'sprinkler', 'tank',
    ]);
  });

  it('filters case-insensitively across Tamil, English, and whitespace', () => {
    expect(filterIrrigationTypes(options, '  RAIN-FED  ')).toEqual([options[0]]);
    expect(filterIrrigationTypes(options, 'கால்வாய்')).toEqual([options[1]]);
  });

  it('renders selected state, returns the canonical value, and closes', () => {
    const onSelect = jest.fn();
    const onClose = jest.fn();
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(
        <IrrigationTypeSelector
          visible
          options={options}
          selectedValue="canal"
          onSelect={onSelect}
          onClose={onClose}
        />,
      );
    });
    expect(tree.root.findByProps({ testID: 'irrigation-option-canal' }).props.accessibilityState)
      .toEqual({ selected: true });
    act(() => { tree.root.findByProps({ testID: 'irrigation-option-rainfed' }).props.onPress(); });
    expect(onSelect).toHaveBeenCalledWith('rainfed');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes without changing selection and has complete Tamil presentation keys', () => {
    const onSelect = jest.fn();
    const onClose = jest.fn();
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(
        <IrrigationTypeSelector visible options={options} selectedValue="canal" onSelect={onSelect} onClose={onClose} />,
      );
    });
    act(() => { tree.root.findByProps({ testID: 'irrigation-selector-close' }).props.onPress(); });
    expect(onSelect).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(ta.irrigationSelector.title).not.toBe(en.irrigationSelector.title);
    expect(Object.keys(ta.irrigationSelector.descriptions)).toEqual(
      Object.keys(en.irrigationSelector.descriptions),
    );
  });
});
