const React = require('react');
const TestRenderer = require('react-test-renderer');

jest.mock('react-i18next', () => ({ useTranslation: () => ({
  t: (key: string, options?: { confidence?: number }) =>
    key === 'disease.diagnosisConfidence' ? `${options?.confidence}% confidence` : key,
}) }));
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

import { BananaPredictionResult } from '../components/BananaPredictionResult';

test('renders exact disease confidence outside development diagnostics', async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(React.createElement(BananaPredictionResult, {
      response: {
        result: { confidence: 0.873 },
        message_key: 'banana.result.cordana',
        model_version: 'banana-v3.0.0',
        runtime_backend: 'pytorch',
        processing_time_ms: 12,
        decision_code: 'BV3_ACCEPTED',
        healthy_gate: { confidence: 0.95, margin: 0.7 },
        disease_classifier: { confidence: 0.873, margin: 0.3 },
        request_id: 'request-1',
      },
      onRetake: jest.fn(),
      onFeedback: jest.fn(),
    }));
  });
  expect(tree.root.findByProps({ children: '87% confidence' })).toBeTruthy();
});

test.each([undefined, Number.NaN, Number.POSITIVE_INFINITY])(
  'renders confidence unavailable for invalid confidence %p',
  async (confidence) => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(React.createElement(BananaPredictionResult, {
        response: {
          result: { confidence }, message_key: 'banana.result.cordana',
          model_version: 'banana-v3.0.0', runtime_backend: 'pytorch',
          processing_time_ms: 12, decision_code: 'BV3_ACCEPTED',
          healthy_gate: { confidence: 0.95, margin: 0.7 },
          disease_classifier: { confidence, margin: 0.3 }, request_id: 'request-1',
        },
        onRetake: jest.fn(), onFeedback: jest.fn(),
      }));
    });
    expect(tree.root.findByProps({ children: 'disease.confidenceUnavailable' })).toBeTruthy();
    expect(tree.root.findAll((node: any) =>
      typeof node.props.children === 'string' && node.props.children.includes('NaN%'),
    )).toHaveLength(0);
  },
);
