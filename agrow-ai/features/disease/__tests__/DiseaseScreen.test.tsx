const mockReact = require('react');
const TestRenderer = require('react-test-renderer');

let mockSelectedFarm: { id?: string; crop?: string } | null = {
  id: 'farm-1',
  crop: 'rice',
};
let mockHasToken = true;
const mockSubmit = jest.fn();
const mockIdentifyCrop = jest.fn();
const mockConfirmIdentifiedCrop = jest.fn();
const mockIdentifyCropInternalOnly = jest.fn();
const mockConfirmInternalCrop = jest.fn();
const mockRestrictedPredict = jest.fn();
const mockCropDiagnosisAdapter = jest.fn();
const mockLoadDiseaseRecommendation = jest.fn();
const mockLoadRestrictedRecommendation = jest.fn();
let mockCapabilitiesQuery: any;
const mockRefetchCapabilities = jest.fn();

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (
      key: string,
      options?: { confidence?: number; crop?: string; defaultValue?: string },
    ) => {
      if (key === 'disease.diagnosisConfidence')
        return `${options?.confidence}% confidence`;
      if (key === 'disease.serverErrorTitle')
        return 'Something went wrong on our end.';
      if (key === 'disease.confirmCropAccessibility') return 'Confirm crop';
      if (key === 'disease.chooseCropAccessibility')
        return `Choose ${options?.crop}`;
      if (key === 'disease.takeAnotherImage') return 'Take another image';
      if (key.startsWith('disease.cropNames.')) {
        const crop = key.slice('disease.cropNames.'.length);
        return crop.charAt(0).toUpperCase() + crop.slice(1);
      }
      return options?.defaultValue ?? key;
    },
  }),
}));
jest.mock('expo-router', () => ({
  useRouter: () => ({ back: jest.fn(), push: jest.fn() }),
}));
jest.mock('expo-image', () => ({ Image: 'Image' }));
jest.mock('@/features/organic/chemicalPolicy', () => ({
  useChemicalPolicy: () => 'show',
  applyChemicalPolicy: (items: string[]) => items,
}));
jest.mock('lucide-react-native', () => {
  const { View } = require('react-native');
  return new Proxy({}, { get: () => View });
});
jest.mock('@/hooks/useAppTheme', () => ({
  useAppTheme: () => ({
    colors: {
      text: '#000',
      primary: '#080',
      onPrimary: '#fff',
      warning: '#a60',
    },
  }),
}));
jest.mock('@/hooks/useLanguage', () => ({
  useLanguage: () => ({ language: 'en' }),
}));
jest.mock('@/features/weather', () => ({
  useSelectedFarm: () => ({ selected: mockSelectedFarm }),
  useWeather: () => ({ data: null }),
}));
jest.mock('@/features/auth/store/authStore', () => ({
  useAuthStore: (selector: (state: unknown) => unknown) =>
    selector({ tokens: mockHasToken ? { idToken: 'present' } : null }),
}));
jest.mock('@/features/cropIdentification', () => ({
  identifyCrop: (...args: unknown[]) => mockIdentifyCrop(...args),
  confirmIdentifiedCrop: (...args: unknown[]) =>
    mockConfirmIdentifiedCrop(...args),
  identifyCropInternalOnly: (...args: unknown[]) =>
    mockIdentifyCropInternalOnly(...args),
  confirmInternalCrop: (...args: unknown[]) => mockConfirmInternalCrop(...args),
}));
jest.mock('@/features/multiCropDiagnosis', () => ({
  ...jest.requireActual('@/features/multiCropDiagnosis'),
  cropDiagnosisAdapter: (crop: string) => {
    mockCropDiagnosisAdapter(crop);
    return { predict: mockRestrictedPredict };
  },
  useDiseaseCapabilities: () => mockCapabilitiesQuery,
}));
jest.mock('../services/recommendationApi', () => ({
  loadDiseaseRecommendation: (...args: unknown[]) =>
    mockLoadDiseaseRecommendation(...args),
  loadRestrictedDiseaseRecommendation: (...args: unknown[]) =>
    mockLoadRestrictedRecommendation(...args),
}));
jest.mock('../components/RecommendationResultCard', () => {
  const { Text } = require('react-native');
  return {
    RecommendationResultCard: ({ recommendation }: any) =>
      mockReact.createElement(
        Text,
        null,
        `recommendation:${recommendation.canonical_disease_name_en}`,
      ),
  };
});
jest.mock('@/features/bananaV3/screens/BananaDiseaseDetectionScreen', () => {
  const { Pressable, Text, View } = require('react-native');
  return {
    BananaDiseaseDetectionScreen: ({
      onChangeCrop,
    }: {
      onChangeCrop: () => void;
    }) =>
      mockReact.createElement(
        View,
        null,
        mockReact.createElement(Text, null, 'banana-v3-screen'),
        mockReact.createElement(Pressable, {
          accessibilityLabel: 'banana-change-crop',
          onPress: onChangeCrop,
        }),
      ),
  };
});
jest.mock('../utils/pickDiseaseImage', () => ({
  captureFromCamera: jest.fn(),
  pickFromGallery: jest.fn(),
  readDiseaseImageBase64: jest.fn(),
}));
jest.mock('@/components/ui', () => {
  const { Pressable, Text, View } = require('react-native');
  return {
    AgScreen: View,
    AgCard: View,
    AgText: Text,
    AgPressable: Pressable,
    AgButton: ({ title, onPress, disabled }: any) =>
      mockReact.createElement(Pressable, {
        accessibilityLabel: title,
        onPress,
        disabled,
      }),
  };
});

import {
  DiseaseScreen,
  validateDiseaseSubmission,
} from '../screens/DiseaseScreen';

beforeEach(() => {
  jest.clearAllMocks();
  mockIdentifyCropInternalOnly.mockReset();
  mockConfirmIdentifiedCrop.mockReset();
  mockConfirmInternalCrop.mockReset();
  mockRestrictedPredict.mockReset();
  const imagePicker = require('../utils/pickDiseaseImage');
  imagePicker.captureFromCamera.mockReset();
  imagePicker.pickFromGallery.mockReset();
  imagePicker.readDiseaseImageBase64.mockReset();
  mockSelectedFarm = { id: 'farm-1', crop: 'rice' };
  mockHasToken = true;
  const crop = (cropId: string, predictionKind: string) => ({
    cropId, visible: true, selectable: true, runtimeReady: true,
    integrityVerified: true, adapterAvailable: true, userAuthorized: true,
    releaseScope: 'internal', fieldValidationStatus: 'IN_PROGRESS',
    supportedClassIds: ['test_class'], predictionKind,
  });
  mockCapabilitiesQuery = {
    isPending: false, isError: false, refetch: mockRefetchCapabilities,
    data: {
      cropIdentification: { ...crop('crop_identification', 'legacy_joint'), predictionKind: null },
      crops: [
        crop('banana', 'banana_v3'), crop('rice', 'legacy_joint'),
        crop('cotton', 'legacy_joint'), crop('groundnut', 'legacy_joint'),
        crop('chilli', 'restricted'), crop('redgram', 'restricted'),
      ],
    },
  };
  mockIdentifyCropInternalOnly.mockRejectedValue(
    new Error('MODEL_NOT_AVAILABLE'),
  );
  mockConfirmIdentifiedCrop.mockResolvedValue({
    request_id: '0123456789abcdef0123456789abcdef',
    confirmed_crop: 'banana',
    crop_source: 'gemini_confirmed',
    confirmation_token: 'a'.repeat(43),
    confirmed_at: '2026-08-03T00:00:00Z',
    expires_at: '2026-08-03T00:15:00Z',
  });
  mockConfirmInternalCrop.mockResolvedValue({
    request_id: 'fedcba9876543210fedcba9876543210',
    confirmed_crop: 'chilli',
    crop_source: 'internal_six_class_confirmed',
    confirmation_token: 'r'.repeat(43),
    confirmed_at: '2026-08-03T00:00:00Z',
    expires_at: '2026-08-03T00:15:00Z',
  });
});

// Regression coverage for the 2026-08 pre-release production bug: a
// TESTER_ROLE_REQUIRED capability snapshot is what every regular (non-tester)
// farmer's account looks like -- disabledReason is assigned by
// `!userAuthorized` before any other check (features/multiCropDiagnosis/cropRegistry.ts),
// so this state is not a distinct "blocked" category, it *is* "regular farmer".
// This test used to assert such users were blocked with 'disease.testerRoleRequired',
// which was itself the bug: it encoded the exact behavior that made disease
// detection unreachable for every real farmer in production. Updated to assert
// the fixed, intended behavior -- routed to the general-release diagnosis flow.
test('non-tester farmers are routed to the general-release diagnosis flow, not blocked', async () => {
  mockCapabilitiesQuery = {
    isPending: false, isError: false, refetch: mockRefetchCapabilities,
    data: {
      crops: [],
      cropIdentification: {
        cropId: 'crop_identification', visible: true, selectable: false,
        runtimeReady: true, integrityVerified: true, adapterAvailable: true,
        userAuthorized: false, releaseScope: 'internal', fieldValidationStatus: 'IN_PROGRESS',
        supportedClassIds: [], predictionKind: null, disabledReason: 'TESTER_ROLE_REQUIRED',
      },
    },
  };
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  expect(tree.root.findByProps({ testID: 'general-diagnosis-screen' })).toBeTruthy();
  expect(tree.root.findAllByProps({ children: 'disease.testerRoleRequired' })).toHaveLength(0);
  expect(mockIdentifyCropInternalOnly).not.toHaveBeenCalled();
});

// A genuinely still-blocked population: an authorized tester (userAuthorized:
// true, so this is NOT the TESTER_ROLE_REQUIRED/regular-farmer case above)
// whose crop-identification model isn't ready yet. This must still show the
// blocking screen -- the fix above only reroutes the "not a tester" case.
test('testers with an unavailable model are still blocked from crop identification', async () => {
  mockCapabilitiesQuery = {
    isPending: false, isError: false, refetch: mockRefetchCapabilities,
    data: {
      crops: [],
      cropIdentification: {
        cropId: 'crop_identification', visible: true, selectable: false,
        runtimeReady: false, integrityVerified: true, adapterAvailable: true,
        userAuthorized: true, releaseScope: 'internal', fieldValidationStatus: 'IN_PROGRESS',
        supportedClassIds: [], predictionKind: null, disabledReason: 'RUNTIME_NOT_READY',
      },
    },
  };
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  expect(tree.root.findAllByProps({ testID: 'general-diagnosis-screen' })).toHaveLength(0);
  expect(tree.root.findAllByProps({ accessibilityLabel: 'disease.takePhoto' })).toHaveLength(0);
  expect(mockIdentifyCropInternalOnly).not.toHaveBeenCalled();
});

test('capability failure provides retry and back UX without exposing capture', async () => {
  mockCapabilitiesQuery = {
    isPending: false, isError: true, data: undefined, refetch: mockRefetchCapabilities,
  };
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: 'disease.retryCapabilities' }).props.onPress();
  });
  expect(mockRefetchCapabilities).toHaveBeenCalledTimes(1);
  expect(tree.root.findAllByProps({ accessibilityLabel: 'disease.takePhoto' })).toHaveLength(0);
  expect(tree.root.findByProps({ accessibilityLabel: 'common.back' })).toBeTruthy();
});

test('zero authorized crops is a recoverable blocked state', async () => {
  mockCapabilitiesQuery = {
    isPending: false, isError: false, refetch: mockRefetchCapabilities,
    data: {
      crops: [],
      cropIdentification: {
        cropId: 'crop_identification', visible: true, selectable: true,
        runtimeReady: true, integrityVerified: true, adapterAvailable: true,
        userAuthorized: true, releaseScope: 'internal', fieldValidationStatus: 'IN_PROGRESS',
        supportedClassIds: [], predictionKind: null,
      },
    },
  };
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  expect(tree.root.findByProps({ children: 'disease.noCropsAvailable' })).toBeTruthy();
  expect(tree.root.findByProps({ accessibilityLabel: 'disease.retryCapabilities' })).toBeTruthy();
  expect(tree.root.findByProps({ accessibilityLabel: 'common.back' })).toBeTruthy();
});

test('replacing a confirmed non-Banana photo reruns crop identification before analysis', async () => {
  mockIdentifyCropInternalOnly
    .mockResolvedValueOnce({
      request_id: 'request-a', status: 'identified', identified_crop: 'paddy',
      confidence: 0.9, margin: 0.7, calibrated_probabilities: { paddy: 0.9 },
      farmer_confirmation_required: true,
    })
    .mockResolvedValueOnce({
      request_id: 'request-b', status: 'identified', identified_crop: 'paddy',
      confidence: 0.88, margin: 0.65, calibrated_probabilities: { paddy: 0.88 },
      farmer_confirmation_required: true,
    });
  const picker = require('../utils/pickDiseaseImage').pickFromGallery as jest.Mock;
  picker
    .mockResolvedValueOnce({ uri: 'file://first.jpg', mimeType: 'image/jpeg', width: 1000, height: 1000, fileSize: 100000 })
    .mockResolvedValueOnce({ uri: 'file://replacement.jpg', mimeType: 'image/jpeg', width: 1000, height: 1000, fileSize: 100000 });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: 'Confirm crop' }).props.onPress();
    await Promise.resolve();
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: 'disease.retakePhoto' }).props.onPress();
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: 'disease.chooseGallery' }).props.onPress();
    await Promise.resolve();
  });
  expect(mockIdentifyCropInternalOnly).toHaveBeenCalledTimes(2);
  expect(mockConfirmInternalCrop).toHaveBeenCalledTimes(1);
  expect(mockRestrictedPredict).not.toHaveBeenCalled();
  expect(tree.root.findByProps({ accessibilityLabel: 'Confirm crop' })).toBeTruthy();
});

async function pickPhoto(tree: any) {
  await TestRenderer.act(async () => {
    await tree.root
      .findByProps({ accessibilityLabel: 'disease.chooseGallery' })
      .props.onPress();
  });
}

test('active disease route mounts', async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  expect(tree.root).toBeTruthy();
});

test('entry screen preserves the safety warning and camera capture pipeline', async () => {
  const camera = require('../utils/pickDiseaseImage')
    .captureFromCamera as jest.Mock;
  camera.mockResolvedValueOnce({
    uri: 'file://camera-leaf.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  expect(
    tree.root.findByProps({ testID: 'disease-detection-screen' }),
  ).toBeTruthy();
  expect(
    tree.root.findByProps({ children: 'disease.cropIdentificationCaution' }),
  ).toBeTruthy();
  expect(
    tree.root.findByProps({ children: 'disease.photoTipMessage' }),
  ).toBeTruthy();
  await TestRenderer.act(async () => {
    await tree.root
      .findByProps({ accessibilityLabel: 'disease.takePhoto' })
      .props.onPress();
  });
  expect(camera).toHaveBeenCalledWith({ base64: false });
  expect(mockIdentifyCropInternalOnly).toHaveBeenCalledTimes(1);
  expect(mockSubmit).not.toHaveBeenCalled();
});

test('photo-first flow shows a server error when crop identification fails unexpectedly', async () => {
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://leaf.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  expect(mockIdentifyCropInternalOnly).toHaveBeenCalledTimes(1);
  expect(mockIdentifyCrop).not.toHaveBeenCalled();
  expect(
    tree.root.findAllByProps({ children: 'Something went wrong on our end.' })
      .length,
  ).toBeGreaterThan(0);
  expect(
    tree.root.findAllByProps({ children: 'banana-v3-screen' }),
  ).toHaveLength(0);
});

test('local image rejection shows and logs the specific quality reason', async () => {
  const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://small-leaf.jpg',
    mimeType: 'image/jpeg',
    width: 100,
    height: 800,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);

  expect(mockIdentifyCropInternalOnly).not.toHaveBeenCalled();
  expect(
    tree.root.findByProps({
      children: 'disease.identificationQualityTooSmall',
    }),
  ).toBeTruthy();
  expect(warn).toHaveBeenCalledWith(
    '[DiseaseScreen]',
    'image quality check failed:',
    'too_small',
  );
  warn.mockRestore();
});

test('identified Banana requires explicit confirmation before Banana flow opens', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: '0123456789abcdef0123456789abcdef',
    status: 'identified',
    identified_crop: 'banana',
    confidence: 0.96,
    calibrated_probabilities: {
      banana: 0.96,
      paddy: 0.02,
      cotton: 0.01,
      groundnut: 0.005,
      chilli: 0.003,
      redgram: 0.002,
    },
    margin: 0.94,
    farmer_confirmation_required: true,
    reason_code: 'CROP_MATCH',
  });
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://leaf.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  expect(
    tree.root.findAllByProps({ children: 'banana-v3-screen' }),
  ).toHaveLength(0);
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: 'Confirm crop' })
      .props.onPress();
  });
  expect(
    tree.root.findAllByProps({ children: 'banana-v3-screen' }).length,
  ).toBeGreaterThan(0);
});

test('crop suggestion shows confidence unavailable instead of NaN', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: '0123456789abcdef0123456789abcdef',
    status: 'identified',
    identified_crop: 'banana',
    confidence: undefined,
    calibrated_probabilities: {},
    margin: 0.8,
    farmer_confirmation_required: true,
    reason_code: 'CROP_MATCH',
  });
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://leaf.jpg', mimeType: 'image/jpeg',
    width: 1000, height: 1000, fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  expect(
    tree.root.findByProps({ children: 'disease.confidenceUnavailable' }),
  ).toBeTruthy();
  expect(tree.root.findAll((node: any) =>
    typeof node.props.children === 'string' && node.props.children.includes('NaN%'),
  )).toHaveLength(0);
});

test.each(['Paddy', 'Cotton', 'Groundnut'])(
  '%s uses an explicit confirmation gate and never starts disease inference',
  async (choice) => {
    mockIdentifyCropInternalOnly.mockResolvedValueOnce({
      request_id: '0123456789abcdef0123456789abcdef',
      status: 'uncertain',
      identified_crop: null,
      confidence: null,
      calibrated_probabilities: {
        banana: 0.2,
        paddy: 0.2,
        cotton: 0.2,
        groundnut: 0.15,
        chilli: 0.15,
        redgram: 0.1,
      },
      margin: 0,
      farmer_confirmation_required: true,
      reason_code: 'CROP_IDENTITY_UNCERTAIN',
    });
    const picker = require('../utils/pickDiseaseImage')
      .pickFromGallery as jest.Mock;
    picker.mockResolvedValueOnce({
      uri: 'file://leaf.jpg',
      mimeType: 'image/jpeg',
      width: 1000,
      height: 1000,
      fileSize: 100000,
    });
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
    });
    await pickPhoto(tree);
    await TestRenderer.act(async () => {
      tree.root
        .findByProps({ accessibilityLabel: `Choose ${choice}` })
        .props.onPress();
    });
    expect(
      tree.root.findByProps({ accessibilityLabel: 'Confirm crop' }),
    ).toBeTruthy();
    expect(
      tree.root.findAllByProps({ children: 'banana-v3-screen' }),
    ).toHaveLength(0);
    expect(mockSubmit).not.toHaveBeenCalled();
  },
);

test('changing crop clears the selected image and result flow', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: '0123456789abcdef0123456789abcdef',
    status: 'uncertain',
    identified_crop: null,
    confidence: null,
    calibrated_probabilities: {
      banana: 0.2,
      paddy: 0.2,
      cotton: 0.2,
      groundnut: 0.15,
      chilli: 0.15,
      redgram: 0.1,
    },
    margin: 0,
    farmer_confirmation_required: true,
    reason_code: 'CROP_IDENTITY_UNCERTAIN',
  });
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://leaf.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  await TestRenderer.act(async () =>
    tree.root
      .findByProps({ accessibilityLabel: 'Choose Paddy' })
      .props.onPress(),
  );
  await TestRenderer.act(async () =>
    tree.root
      .findByProps({ accessibilityLabel: 'Take another image' })
      .props.onPress(),
  );
  expect(
    tree.root.findByProps({ accessibilityLabel: 'disease.takePhoto' }),
  ).toBeTruthy();
  expect(tree.root.findAllByType('Image')).toHaveLength(0);
});

test('an already-used crop confirmation shows the specific replay message', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: '0123456789abcdef0123456789abcdef',
    status: 'identified',
    identified_crop: 'paddy',
    confidence: 0.9,
    margin: 0.7,
    calibrated_probabilities: {
      banana: 0.02,
      paddy: 0.9,
      cotton: 0.02,
      groundnut: 0.02,
      chilli: 0.02,
      redgram: 0.02,
    },
    farmer_confirmation_required: true,
  });
  mockConfirmInternalCrop.mockRejectedValueOnce(
    new Error('CROP_CONFIRMATION_ALREADY_USED'),
  );
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://leaf.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: 'Confirm crop' })
      .props.onPress();
    await Promise.resolve();
  });

  expect(
    tree.root.findByProps({
      children: 'disease.photoAlreadyConfirmed',
    }),
  ).toBeTruthy();
  expect(
    tree.root.findAllByProps({
      children: 'disease.errorConfirmCrop',
    }),
  ).toHaveLength(0);
});

test.each(['rice', 'paddy', 'cotton', 'groundnut'])(
  'verified crop %s passes the model eligibility guard',
  (crop) => {
    expect(
      validateDiseaseSubmission({
        imagePresent: true,
        crop,
        mimeType: 'image/jpeg',
        tokenPresent: true,
        requestRunning: false,
      }),
    ).toBeNull();
  },
);

test.each(['chilli', 'redgram'])(
  'restricted crop %s may enter the authenticated backend flow',
  (crop) => {
    expect(
      validateDiseaseSubmission({
        imagePresent: true,
        crop,
        mimeType: 'image/jpeg',
        tokenPresent: true,
        requestRunning: false,
      }),
    ).toBeNull();
  },
);

test('missing authentication is reported before model eligibility', () => {
  expect(
    validateDiseaseSubmission({
      imagePresent: true,
      crop: 'rice',
      mimeType: 'image/jpeg',
      tokenPresent: false,
      requestRunning: false,
    }),
  ).toBe('authentication_unavailable');
});

test('request-running guard remains first', () => {
  expect(
    validateDiseaseSubmission({
      imagePresent: true,
      crop: 'banana',
      mimeType: 'image/jpeg',
      tokenPresent: true,
      requestRunning: true,
    }),
  ).toBe('request_already_running');
});

test('a dropdown entry never triggers the legacy diagnosis client', async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  expect(tree.root).toBeTruthy();
  expect(mockSubmit).not.toHaveBeenCalled();
});

test('accepted chilli dispatches to restricted inference and authenticated recommendation lookup', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: 'fedcba9876543210fedcba9876543210',
    status: 'identified',
    identified_crop: 'chilli',
    confidence: 0.42,
    margin: 0.1,
    calibrated_probabilities: {
      chilli: 0.42,
      redgram: 0.32,
      banana: 0.08,
      paddy: 0.07,
      cotton: 0.06,
      groundnut: 0.05,
    },
    farmer_confirmation_required: true,
  });
  mockRestrictedPredict.mockResolvedValueOnce({
    outcome: 'accepted',
    crop_id: 'chilli',
    crop_identity_source: 'user_confirmed_not_ai_verified',
    class_id: 'chilli__bacterial_spot',
    qualitative_confidence: 'high',
    calibrated_confidence: 0.88,
    margin: 0.25,
    accepted: true,
    official_accuracy_claim: false,
    field_validation_status: 'IN_PROGRESS',
    test_mode: {
      active: true,
      code: 'RESTRICTED_CROP_CONTROLLED_TEST',
      display_required: true,
      banner_text:
        'TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED',
    },
  });
  mockLoadRestrictedRecommendation.mockResolvedValueOnce({
    outcome: 'RECOMMENDATION_PARTIAL',
    canonical_disease_name_en: 'Bacterial spot',
    canonical_disease_name_ta: 'பாக்டீரியா இலைப்புள்ளி',
  });
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://leaf.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  expect(
    tree.root.findByProps({ children: 'disease.runnerUpCrop' }),
  ).toBeTruthy();
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: 'Confirm crop' })
      .props.onPress();
    await Promise.resolve();
  });
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: 'disease.analyze' })
      .props.onPress();
    await Promise.resolve();
  });
  expect(mockRestrictedPredict).toHaveBeenCalledWith(
    expect.objectContaining({
      cropConfirmationToken: 'r'.repeat(43),
      farmId: 'farm-1',
    }),
  );
  expect(mockLoadRestrictedRecommendation).toHaveBeenCalledWith(
    'chilli',
    'chilli__bacterial_spot',
  );
  expect(
    tree.root.findByProps({
      children:
        'TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED',
    }),
  ).toBeTruthy();
  expect(
    tree.root.findByProps({ children: 'recommendation:Bacterial spot' }),
  ).toBeTruthy();
  expect(tree.root.findByProps({ children: '88% confidence' })).toBeTruthy();
});

test.each([
  ['paddy', 'rice_blast', false],
  ['cotton', 'cotton_fusarium_wilt', false],
  ['groundnut', 'groundnut_rust', false],
  ['chilli', 'chilli__bacterial_spot', true],
  ['redgram', 'redgram__sterility_mosaic', true],
] as const)(
  'accepted %s result shows treatment verification fallback when lookup fails',
  async (crop, classId, restricted) => {
    mockIdentifyCropInternalOnly.mockResolvedValueOnce({
      request_id: 'fedcba9876543210fedcba9876543210',
      status: 'identified',
      identified_crop: crop,
      confidence: 0.9,
      margin: 0.7,
      calibrated_probabilities: { [crop]: 0.9 },
      farmer_confirmation_required: true,
    });
    mockConfirmInternalCrop.mockResolvedValueOnce({
      request_id: 'fedcba9876543210fedcba9876543210',
      confirmed_crop: crop,
      crop_source: 'internal_six_class_confirmed',
      confirmation_token: `${crop[0]}`.repeat(43),
      confirmed_at: '2026-08-03T00:00:00Z',
      expires_at: '2026-08-03T00:15:00Z',
    });
    mockRestrictedPredict.mockResolvedValueOnce({
      outcome: 'accepted',
      crop_id: crop === 'paddy' ? 'rice' : crop,
      crop_identity_source: 'user_confirmed_not_ai_verified',
      class_id: classId,
      qualitative_confidence: 'high',
      calibrated_confidence: 0.88,
      margin: 0.25,
      accepted: true,
      official_accuracy_claim: false,
      field_validation_status: 'IN_PROGRESS',
      test_mode: restricted
        ? {
            active: true,
            code: 'RESTRICTED_CROP_CONTROLLED_TEST',
            display_required: true,
            banner_text:
              'TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED',
          }
        : null,
    });
    (restricted
      ? mockLoadRestrictedRecommendation
      : mockLoadDiseaseRecommendation
    ).mockRejectedValueOnce(new Error('lookup timeout'));
    const picker = require('../utils/pickDiseaseImage')
      .pickFromGallery as jest.Mock;
    picker.mockResolvedValueOnce({
      uri: `file://${crop}.jpg`,
      mimeType: 'image/jpeg',
      width: 1000,
      height: 1000,
      fileSize: 100000,
    });
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
    });
    await pickPhoto(tree);
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: 'Confirm crop' }).props.onPress();
      await Promise.resolve();
    });
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: 'disease.analyze' }).props.onPress();
      await Promise.resolve();
    });

    expect(
      tree.root.findByProps({
        children: 'banana.ui.treatmentPendingVerification',
      }),
    ).toBeTruthy();
  },
);

test.each([
  ['paddy', 'rice', 'rice_blast', false],
  ['cotton', 'cotton', 'cotton_fusarium_wilt', false],
  ['groundnut', 'groundnut', 'groundnut_rust', false],
  ['redgram', 'redgram', 'redgram__sterility_mosaic', true],
] as const)(
  '%s confirmation enables Analyze and dispatches the crop-specific prediction',
  async (crop, adapterCrop, classId, restricted) => {
    const token = crop[0].repeat(43);
    mockIdentifyCropInternalOnly.mockResolvedValueOnce({
      request_id: '0123456789abcdef0123456789abcdef',
      status: 'identified',
      identified_crop: crop,
      confidence: 0.9,
      margin: 0.7,
      calibrated_probabilities: { [crop]: 0.9 },
      farmer_confirmation_required: true,
    });
    mockConfirmInternalCrop.mockResolvedValueOnce({
      request_id: '0123456789abcdef0123456789abcdef',
      confirmed_crop: crop,
      crop_source: 'internal_six_class_confirmed',
      confirmation_token: token,
      confirmed_at: '2026-08-03T00:00:00Z',
      expires_at: '2026-08-03T00:15:00Z',
    });
    mockRestrictedPredict.mockResolvedValueOnce({
      outcome: 'accepted',
      crop_id: crop,
      crop_identity_source: 'user_confirmed_not_ai_verified',
      class_id: classId,
      qualitative_confidence: 'high',
      calibrated_confidence: 0.88,
      margin: 0.25,
      accepted: true,
      official_accuracy_claim: false,
      field_validation_status: 'IN_PROGRESS',
      test_mode: restricted
        ? {
            active: true,
            code: 'RESTRICTED_CROP_CONTROLLED_TEST',
            display_required: true,
            banner_text:
              'TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED',
          }
        : null,
    });
    const recommendation = {
      outcome: 'RECOMMENDATION_PARTIAL',
      canonical_disease_name_en: `${crop} recommendation`,
      canonical_disease_name_ta: `${crop} recommendation`,
    };
    (restricted
      ? mockLoadRestrictedRecommendation
      : mockLoadDiseaseRecommendation
    ).mockResolvedValueOnce(recommendation);
    const picker = require('../utils/pickDiseaseImage')
      .pickFromGallery as jest.Mock;
    picker.mockResolvedValueOnce({
      uri: `file://${crop}.jpg`,
      mimeType: 'image/jpeg',
      width: 1000,
      height: 1000,
      fileSize: 100000,
    });
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
    });
    await pickPhoto(tree);
    await TestRenderer.act(async () => {
      tree.root.findByProps({ accessibilityLabel: 'Confirm crop' }).props.onPress();
      await Promise.resolve();
    });
    const analyze = tree.root.findByProps({
      accessibilityLabel: 'disease.analyze',
    });
    expect(analyze.props.disabled).toBe(false);

    await TestRenderer.act(async () => {
      analyze.props.onPress();
      await Promise.resolve();
    });

    expect(mockCropDiagnosisAdapter).toHaveBeenCalledWith(adapterCrop);
    expect(mockRestrictedPredict).toHaveBeenCalledWith(
      expect.objectContaining({
        uri: `file://${crop}.jpg`,
        mimeType: 'image/jpeg',
        cropConfirmed: true,
        cropConfirmationToken: token,
        farmId: 'farm-1',
      }),
    );
    expect(
      tree.root.findByProps({ children: `recommendation:${crop} recommendation` }),
    ).toBeTruthy();
  },
);

test('successful legacy analysis disables Analyze and blocks a second request with the consumed token', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: '0123456789abcdef0123456789abcdef',
    status: 'identified',
    identified_crop: 'paddy',
    confidence: 0.91,
    margin: 0.72,
    calibrated_probabilities: {
      banana: 0.01,
      paddy: 0.91,
      cotton: 0.03,
      groundnut: 0.02,
      chilli: 0.02,
      redgram: 0.01,
    },
    farmer_confirmation_required: true,
  });
  mockConfirmInternalCrop.mockResolvedValueOnce({
    request_id: '0123456789abcdef0123456789abcdef',
    confirmed_crop: 'paddy',
    crop_source: 'internal_six_class_confirmed',
    confirmation_token: 'p'.repeat(43),
    confirmed_at: '2026-08-03T00:00:00Z',
    expires_at: '2026-08-03T00:15:00Z',
  });
  mockRestrictedPredict.mockResolvedValueOnce({
    outcome: 'accepted',
    crop_id: 'rice',
    crop_identity_source: 'user_confirmed_not_ai_verified',
    class_id: 'rice_blast',
    qualitative_confidence: 'high',
    calibrated_confidence: 0.86,
    accepted: true,
    official_accuracy_claim: false,
    field_validation_status: 'IN_PROGRESS',
  });
  mockLoadDiseaseRecommendation.mockResolvedValueOnce(null);
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://paddy.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: 'Confirm crop' })
      .props.onPress();
    await Promise.resolve();
  });

  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: 'disease.analyze' })
      .props.onPress();
    await Promise.resolve();
  });

  const analyzeButton = tree.root.findByProps({
    accessibilityLabel: 'disease.analyze',
  });
  expect(analyzeButton.props.disabled).toBe(true);
  expect(mockRestrictedPredict).toHaveBeenCalledTimes(1);

  await TestRenderer.act(async () => {
    analyzeButton.props.onPress();
    await Promise.resolve();
  });
  expect(mockRestrictedPredict).toHaveBeenCalledTimes(1);
});

test('redgram can be suggested directly by the unified first-photo identifier', async () => {
  mockIdentifyCropInternalOnly.mockResolvedValueOnce({
    request_id: 'abcdefabcdefabcdefabcdefabcdefab',
    status: 'identified',
    identified_crop: 'redgram',
    confidence: 0.4,
    margin: 0.13,
    calibrated_probabilities: {
      banana: 0.1,
      paddy: 0.09,
      cotton: 0.08,
      groundnut: 0.06,
      chilli: 0.27,
      redgram: 0.4,
    },
    farmer_confirmation_required: true,
  });
  const picker = require('../utils/pickDiseaseImage')
    .pickFromGallery as jest.Mock;
  picker.mockResolvedValueOnce({
    uri: 'file://redgram.jpg',
    mimeType: 'image/jpeg',
    width: 1000,
    height: 1000,
    fileSize: 100000,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(DiseaseScreen));
  });
  await pickPhoto(tree);
  expect(mockIdentifyCropInternalOnly).toHaveBeenCalledTimes(1);
  expect(mockIdentifyCrop).not.toHaveBeenCalled();
  expect(
    tree.root.findByProps({ accessibilityLabel: 'Confirm crop' }),
  ).toBeTruthy();
  expect(
    tree.root.findByProps({ children: 'disease.runnerUpCrop' }),
  ).toBeTruthy();
});
