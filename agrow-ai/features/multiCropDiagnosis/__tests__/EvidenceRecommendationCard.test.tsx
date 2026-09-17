const React = require('react');
const TestRenderer = require('react-test-renderer');

jest.mock('@/components/ui', () => {
  const { Text, View } = require('react-native');
  return { AgCard: View, AgText: Text };
});

import { EvidenceRecommendationCard } from '../components/EvidenceRecommendationCard';

async function renderText(element: React.ReactElement): Promise<string> {
  let renderer: any;
  await TestRenderer.act(async () => {
    renderer = TestRenderer.create(element);
  });
  return JSON.stringify(renderer.toJSON());
}

test('fails closed when recommendation evidence is absent', async () => {
  const output = await renderText(
    <EvidenceRecommendationCard recommendation={null} language="ta" />,
  );
  expect(output).toContain('disease.verifyQualifiedSource');
});

test('marks missing Tamil translation for review instead of inventing it', async () => {
  const output = await renderText(
    <EvidenceRecommendationCard
      language="ta"
      recommendation={{
        verification_label: 'VERIFY AGAINST OFFICIAL SOURCE',
        official_diagnosis: false,
        field_validated: false,
        display_name: { en: 'Source disease name', ta: null, tamil_review_required: true },
        items: [],
      }}
    />,
  );
  expect(output).toContain('Source disease name');
  expect(output).not.toContain('REVIEW_REQUIRED');
});
