const React = require('react');
const TestRenderer = require('react-test-renderer');

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { confidence?: number }) =>
      key === 'disease.diagnosisConfidence' ? `${options?.confidence}% confidence` : key,
  }),
}));

jest.mock('@/components/ui', () => {
  const MockReact = require('react');
  const { Pressable, Text, View } = require('react-native');
  return {
    AgCard: View,
    AgText: Text,
    AgButton: ({ title, onPress }: any) =>
      MockReact.createElement(Pressable, { accessibilityLabel: title, onPress }),
  };
});

import { AcceptedDiagnosisCard, UncertainDiagnosisCard } from '../components/DiagnosisStates';

test('nutrient navigation is offered only for an uncertain outcome', async () => {
  const onCheckNutrients = jest.fn();
  let uncertain: any;
  await TestRenderer.act(async () => {
    uncertain = TestRenderer.create(
      React.createElement(UncertainDiagnosisCard, {
        onRetake: jest.fn(),
        onCheckNutrients,
      }),
    );
  });
  expect(uncertain.root.findByProps({ accessibilityLabel: 'disease.checkNutrientSymptoms' })).toBeTruthy();

  let accepted: any;
  await TestRenderer.act(async () => {
    accepted = TestRenderer.create(
      React.createElement(AcceptedDiagnosisCard, {
        title: 'rice blast',
        explanation: 'accepted',
        confidence: 0.87,
        onFeedback: jest.fn(),
      }),
    );
  });
  expect(accepted.root.findAllByProps({ accessibilityLabel: 'disease.checkNutrientSymptoms' })).toHaveLength(0);
  expect(accepted.root.findByProps({ children: '87% confidence' })).toBeTruthy();
});

test('accepted diagnosis fails safely when confidence is not finite', async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(React.createElement(AcceptedDiagnosisCard, {
      title: 'rice blast', explanation: 'accepted', confidence: Number.NaN,
      onFeedback: jest.fn(),
    }));
  });
  expect(tree.root.findByProps({ children: 'disease.confidenceUnavailable' })).toBeTruthy();
});
