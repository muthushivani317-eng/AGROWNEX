const mockReact = require('react');
const TestRenderer = require('react-test-renderer');

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? _key,
  }),
}));
jest.mock('@/components/ui', () => {
  return {
    AgBadge: ({ label }: any) => mockReact.createElement('Text', null, label),
    AgCard: ({ children }: any) => mockReact.createElement('View', null, children),
    AgText: ({ children }: any) => mockReact.createElement('Text', null, children),
  };
});

import { GroundnutPestObservationStatus } from '../components/GroundnutPestObservationStatus';

async function rendered(observation: any): Promise<string> {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(GroundnutPestObservationStatus, { observation }),
    );
  });
  return JSON.stringify(tree.toJSON());
}

test('shows a pending Groundnut observation without pest identification or confidence', async () => {
  const output = await rendered({
    damageExtent: 'several',
    spreadSpeed: 'rapid',
    reviewStatus: 'pending',
    feedback: null,
    reviewTimestamp: null,
  });
  expect(output).toContain('Pending expert review');
  expect(output).toContain('waiting for KVK review');
  expect(output).not.toContain('confidence');
  expect(output).not.toContain('Aphid');
});

test('shows predefined reviewed feedback as non-diagnostic guidance', async () => {
  const output = await rendered({
    damageExtent: 'few',
    spreadSpeed: 'stable',
    reviewStatus: 'reviewed',
    feedback: 'submit_clearer_photo',
    reviewTimestamp: '2026-11-13T00:00:00Z',
  });
  expect(output).toContain('Reviewed');
  expect(output).toContain('Submit a clearer photograph');
  expect(output).toContain('do not identify a pest');
  expect(output).not.toContain('confidence');
});
