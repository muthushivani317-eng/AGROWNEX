const mockReact = require('react');
const TestRenderer = require('react-test-renderer');
const mockIdentifyPlant = jest.fn();
const mockPick = jest.fn();
const mockRouterPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));
jest.mock('expo-location', () => ({
  Accuracy: { Balanced: 3 },
  getForegroundPermissionsAsync: jest.fn().mockResolvedValue({ granted: false }),
  getCurrentPositionAsync: jest.fn(),
}));

jest.mock('expo-image', () => ({ Image: 'Image' }));
jest.mock('lucide-react-native', () => {
  const { View } = require('react-native');
  return new Proxy({}, { get: () => View });
});
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock('@/hooks/useAppTheme', () => ({
  useAppTheme: () => ({ colors: { primary: '#080', onPrimary: '#fff' } }),
}));
jest.mock('@/hooks/useLanguage', () => ({
  useLanguage: () => ({ language: 'ta' }),
}));
jest.mock('@/features/growth/components/ImageViewer', () => ({ ImageViewer: 'ImageViewer' }));
jest.mock('@/features/disease/utils/imageQuality', () => ({
  checkImageQuality: () => ({ issues: [] }),
}));
jest.mock('@/features/disease/utils/pickDiseaseImage', () => ({
  captureFromCamera: (...args: unknown[]) => mockPick(...args),
  pickFromGallery: (...args: unknown[]) => mockPick(...args),
}));
jest.mock('../plantIdentifierApi', () => ({
  identifyPlant: (...args: unknown[]) => mockIdentifyPlant(...args),
}));
jest.mock('../services/plantJournalStorage', () => ({
  plantJournalStorage: { add: jest.fn(), list: jest.fn(() => []), remove: jest.fn() },
}));
jest.mock('@/components/ui', () => {
  const { Pressable, Text, View } = require('react-native');
  return {
    AgScreen: View, AgCard: View, AgText: Text,
    AgPressable: ({ children, onPress, accessibilityLabel }: any) =>
      mockReact.createElement(Pressable, { accessibilityLabel, onPress }, children),
    AgButton: ({ title, onPress, disabled }: any) =>
      mockReact.createElement(Pressable, { accessibilityLabel: title, onPress, disabled }),
  };
});

import { PlantIdentifierScreen } from '../PlantIdentifierScreen';

const image = {
  uri: 'file://plant.jpg', mimeType: 'image/jpeg',
  width: 1000, height: 1000, fileSize: 100000,
};
const baseResult = {
  request_id: 'request-1', common_name: null, scientific_name: null,
  family: null, description: null, visible_characteristics: [],
  possible_alternatives: [], confidence: 0.4, informational_only: true,
  used_for_disease_routing: false, disease_inference_available: false,
  crop_confirmation_created: false, provider: 'gemini', language: 'ta',
  disclaimer: 'This identification is provided for general knowledge only.',
  processing_status: 'complete', error_code: null, retry_allowed: true,
};

async function renderWithResult(result: object) {
  mockPick.mockResolvedValueOnce(image);
  mockIdentifyPlant.mockResolvedValueOnce(result);
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(PlantIdentifierScreen));
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.chooseGallery' }).props.onPress();
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.identify' }).props.onPress();
  });
  return tree;
}

beforeEach(() => jest.clearAllMocks());

test('renders identified result fields and informational disclaimer', async () => {
  const tree = await renderWithResult({
    ...baseResult, status: 'identified', common_name: 'Example plant',
    scientific_name: 'Planta exemplaris', family: 'Example family',
    description: 'Broad green leaves.', visible_characteristics: ['Broad leaves'],
    confidence: 0.9, retry_allowed: false,
  });
  expect(tree.root.findByProps({ children: 'Example plant' })).toBeTruthy();
  expect(tree.root.findByProps({ children: 'Planta exemplaris' })).toBeTruthy();
  expect(JSON.stringify(tree.toJSON())).toContain('"90"');
  expect(JSON.stringify(tree.toJSON())).toContain('"% "');
  expect(JSON.stringify(tree.toJSON())).toContain('plantIdentifier.confidence');
  expect(JSON.stringify(tree.toJSON())).toContain('plantIdentifier.family');
  expect(tree.root.findByProps({ children: baseResult.disclaimer })).toBeTruthy();
  expect(tree.root.findAllByProps({ accessibilityLabel: 'Detect disease' })).toHaveLength(0);
  expect(tree.root.findAllByProps({ accessibilityLabel: 'Continue to Disease Detection' })).toHaveLength(0);
});

test('renders uncertain alternatives without disease routing action', async () => {
  const tree = await renderWithResult({
    ...baseResult, status: 'uncertain',
    possible_alternatives: [{
      common_name: 'Alternative', scientific_name: 'Planta altera', confidence: 0.3,
    }],
  });
  expect(tree.root.findByProps({ children: 'plantIdentifier.uncertainTitle' })).toBeTruthy();
  expect(JSON.stringify(tree.toJSON())).toContain('Planta altera');
  expect(tree.root.findAllByProps({ accessibilityLabel: 'Detect disease' })).toHaveLength(0);
});

test.each([
  ['non_plant', 'plantIdentifier.nonPlantTitle'],
  ['invalid_image', 'plantIdentifier.invalidImageTitle'],
  ['provider_error', 'plantIdentifier.providerErrorTitle'],
])('renders %s state safely', async (status, heading) => {
  const tree = await renderWithResult({ ...baseResult, status });
  expect(tree.root.findByProps({ children: heading })).toBeTruthy();
});

test('network failure offers retry and never navigates to disease', async () => {
  mockPick.mockResolvedValueOnce(image);
  mockIdentifyPlant.mockRejectedValueOnce(new Error('network'));
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(PlantIdentifierScreen));
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.chooseGallery' }).props.onPress();
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.identify' }).props.onPress();
  });
  expect(tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.retry' })).toBeTruthy();
  expect(tree.root.findAllByProps({ accessibilityLabel: 'Detect disease' })).toHaveLength(0);
});

test('gallery failure is visible and retryable', async () => {
  mockPick.mockRejectedValueOnce(new Error('permission denied'));
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(PlantIdentifierScreen));
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.chooseGallery' }).props.onPress();
  });
  expect(tree.root.findByProps({ children: 'plantIdentifier.photoAccessFailed' })).toBeTruthy();
  expect(tree.root.findByProps({ accessibilityLabel: 'plantIdentifier.retry' })).toBeTruthy();
});
