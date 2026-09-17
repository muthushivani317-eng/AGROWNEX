const mockReact = require("react");
const TestRenderer = require("react-test-renderer");

const mockPredictBanana = jest.fn();
const mockLoadDiseaseRecommendation = jest.fn();
const mockPickGallery = jest.fn();

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock("expo-router", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("expo-image", () => ({ Image: "Image" }));
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({ colors: { primary: "#080", onPrimary: "#fff" } }),
}));
jest.mock("@/hooks/useLanguage", () => ({
  useLanguage: () => ({ language: "en" }),
}));
jest.mock("@/components/ui", () => {
  const { Pressable, Text, View } = require("react-native");
  return {
    AgScreen: View,
    AgCard: View,
    AgText: Text,
    AgButton: ({ title, onPress, disabled }: any) =>
      mockReact.createElement(Pressable, {
        accessibilityLabel: title,
        onPress,
        disabled,
      }),
  };
});
jest.mock("@/features/multiCropDiagnosis", () => ({
  CropPhotoConfirmation: () => null,
}));
jest.mock(
  "@/features/multiCropDiagnosis/components/VerifiedDiseaseKnowledgeCard",
  () => ({
    VerifiedDiseaseKnowledgeCard: () => null,
  }),
);
jest.mock(
  "@/features/multiCropDiagnosis/components/GuidedDiagnosisCard",
  () => ({
    GuidedDiagnosisCard: () => null,
  }),
);
jest.mock("../components/BananaPredictionResult", () => ({
  BananaPredictionResult: () => null,
}));
jest.mock("../components/BananaUncertainResult", () => ({
  BananaUncertainResult: () => null,
}));
jest.mock("../components/BananaFeedbackSheet", () => ({
  BananaFeedbackSheet: () => null,
}));
jest.mock("../bananaV3Api", () => ({
  predictBanana: (...args: unknown[]) => mockPredictBanana(...args),
  submitBananaFeedback: jest.fn(),
}));
jest.mock("@/features/disease/services/recommendationApi", () => ({
  loadDiseaseRecommendation: (...args: unknown[]) =>
    mockLoadDiseaseRecommendation(...args),
}));
jest.mock("@/features/disease/utils/pickDiseaseImage", () => ({
  captureFromCamera: jest.fn(),
  pickFromGallery: (...args: unknown[]) => mockPickGallery(...args),
}));

import {
  BananaDiseaseDetectionScreen,
  bananaFailureMessageKey,
} from "../screens/BananaDiseaseDetectionScreen";

const basePrediction = {
  request_id: "00000000-0000-4000-8000-000000000001",
  model_version: "banana-v3.0.0",
  crop: "banana",
  status: "accepted",
  decision_code: "BV3_ACCEPTED",
  result: {
    class_id: "banana__cordana_leaf_spot",
    display_name_key: "banana.result.cordana",
    confidence: 0.9,
    margin: 0.4,
  },
  healthy_gate: {
    predicted_class: "banana__diseased",
    confidence: 0.95,
    margin: 0.7,
    accepted: true,
  },
  disease_classifier: {
    predicted_class: "banana__cordana_leaf_spot",
    confidence: 0.9,
    margin: 0.4,
    accepted: true,
    executed: true,
  },
  message_key: "banana.result.cordana",
  requires_follow_up_photo: false,
  requires_human_review: false,
  runtime_backend: "pytorch",
  processing_time_ms: 10,
  timestamp_utc: "2026-08-09T00:00:00Z",
};

const recommendation = (name: string, immediateAction: string) => ({
  canonical_disease_name_en: name,
  canonical_disease_name_ta: name,
  why_it_occurs_en: [],
  why_it_occurs_ta: [],
  symptoms_en: [],
  symptoms_ta: [],
  immediate_actions_en: [immediateAction],
  immediate_actions_ta: [immediateAction],
  cultural_management_en: [],
  cultural_management_ta: [],
  biological_options_en: [],
  biological_options_ta: [],
  nutrient_correction_en: [],
  nutrient_correction_ta: [],
  prevention_en: [],
  prevention_ta: [],
  escalation_conditions_en: [],
  escalation_conditions_ta: [],
  chemical_recommendation_status: "CHEMICAL_RECOMMENDATION_WITHHELD",
  agricultural_disclaimer: "VERIFY AGAINST OFFICIAL SOURCE",
  official_sources: [],
});

async function renderConfirmedBanana() {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://banana.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "confirmed-token",
      }),
    );
  });
  return tree;
}

function renderedTree(tree: any): string {
  return JSON.stringify(tree.toJSON());
}

beforeEach(() => {
  jest.clearAllMocks();
});

test.each([
  [{ status: 0 }, "disease.errors.offline"],
  [
    { status: 403, errorCode: "TESTER_ROLE_REQUIRED" },
    "disease.errors.tester_role_required",
  ],
] as const)("maps Banana transport error to typed key", (error, expected) => {
  expect(bananaFailureMessageKey(error)).toBe(expected);
});

test("receiving the confirmed photo and token after mount automatically starts diagnosis once", async () => {
  mockPredictBanana.mockResolvedValueOnce(basePrediction);
  mockLoadDiseaseRecommendation.mockResolvedValueOnce(null);
  let tree: any;

  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: null,
        cropConfirmationToken: null,
      }),
    );
  });
  expect(mockPredictBanana).not.toHaveBeenCalled();

  await TestRenderer.act(async () => {
    tree.update(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://banana.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "late-confirmed-token",
      }),
    );
  });

  expect(mockPredictBanana).toHaveBeenCalledTimes(1);
  expect(mockPredictBanana).toHaveBeenCalledWith(
    { uri: "file://banana.jpg", mimeType: "image/jpeg" },
    "late-confirmed-token",
    undefined,
  );
});

test("sequential confirmed Banana photos submit once each with their own token", async () => {
  mockPredictBanana
    .mockResolvedValueOnce({
      ...basePrediction,
      decision_code: "BV3_HEALTHY_ACCEPTED",
      result: {
        ...basePrediction.result,
        class_id: "banana__healthy",
        display_name_key: "banana.result.healthy",
      },
      message_key: "banana.result.healthy",
    })
    .mockResolvedValueOnce({
      ...basePrediction,
      decision_code: "BV3_CORDANA_ACCEPTED",
      result: {
        ...basePrediction.result,
        class_id: "banana__cordana_leaf_spot",
        display_name_key: "banana.result.cordana",
      },
      message_key: "banana.result.cordana",
    });
  mockLoadDiseaseRecommendation.mockResolvedValue(null);
  let tree: any;

  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://healthy.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "token-a",
      }),
    );
  });
  await TestRenderer.act(async () => {
    tree.update(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://cordana.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "token-b",
      }),
    );
  });

  expect(mockPredictBanana).toHaveBeenCalledTimes(2);
  expect(mockPredictBanana).toHaveBeenNthCalledWith(
    1,
    { uri: "file://healthy.jpg", mimeType: "image/jpeg" },
    "token-a",
    undefined,
  );
  expect(mockPredictBanana).toHaveBeenNthCalledWith(
    2,
    { uri: "file://cordana.jpg", mimeType: "image/jpeg" },
    "token-b",
    undefined,
  );
});

test("a new confirmed photo is not lost while the previous recommendation is still loading", async () => {
  let resolveRecommendation: (value: null) => void = () => undefined;
  mockPredictBanana
    .mockResolvedValueOnce(basePrediction)
    .mockResolvedValueOnce({
      ...basePrediction,
      decision_code: "BV3_CORDANA_ACCEPTED",
      result: {
        ...basePrediction.result,
        class_id: "banana__cordana_leaf_spot",
        display_name_key: "banana.result.cordana",
      },
      message_key: "banana.result.cordana",
    });
  mockLoadDiseaseRecommendation
    .mockImplementationOnce(
      () =>
        new Promise<null>((resolve) => {
          resolveRecommendation = resolve;
        }),
    )
    .mockResolvedValueOnce(null);
  let tree: any;

  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://healthy.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "token-a",
      }),
    );
    await Promise.resolve();
  });
  expect(mockPredictBanana).toHaveBeenCalledTimes(1);

  await TestRenderer.act(async () => {
    tree.update(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://cordana.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "token-b",
      }),
    );
    await Promise.resolve();
  });
  resolveRecommendation(null);
  await TestRenderer.act(async () => {
    await Promise.resolve();
  });

  expect(mockPredictBanana).toHaveBeenCalledTimes(2);
  expect(mockPredictBanana).toHaveBeenLastCalledWith(
    { uri: "file://cordana.jpg", mimeType: "image/jpeg" },
    "token-b",
    undefined,
  );
});

test("rerendering the same confirmed token does not submit twice", async () => {
  mockPredictBanana.mockResolvedValue(basePrediction);
  mockLoadDiseaseRecommendation.mockResolvedValue(null);
  const props = {
    initialImage: { uri: "file://banana.jpg", mimeType: "image/jpeg" },
    cropConfirmationToken: "same-token",
  };
  let tree: any;

  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(BananaDiseaseDetectionScreen, props),
    );
  });
  await TestRenderer.act(async () => {
    tree.update(
      mockReact.createElement(BananaDiseaseDetectionScreen, { ...props }),
    );
  });

  expect(mockPredictBanana).toHaveBeenCalledTimes(1);
});

test("replacement photo exits to a fresh identification workflow instead of reusing the token", async () => {
  mockPredictBanana.mockResolvedValueOnce(basePrediction);
  mockLoadDiseaseRecommendation.mockResolvedValueOnce(null);
  const onChangeCrop = jest.fn();
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(BananaDiseaseDetectionScreen, {
        initialImage: { uri: "file://banana.jpg", mimeType: "image/jpeg" },
        cropConfirmationToken: "consumable-token",
        onChangeCrop,
      }),
    );
  });
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "banana.ui.replacePhoto" })
      .props.onPress();
  });
  expect(onChangeCrop).toHaveBeenCalledTimes(1);
  expect(mockPickGallery).not.toHaveBeenCalled();
  expect(mockPredictBanana).toHaveBeenCalledTimes(1);
});

test("possibly-consumed network failure offers a fresh-photo action, never retry", async () => {
  mockPredictBanana.mockRejectedValueOnce({
    status: 0,
    errorCode: "network_error",
  });
  const tree = await renderConfirmedBanana();
  expect(
    tree.root.findByProps({ accessibilityLabel: "banana.ui.startFreshPhoto" }),
  ).toBeTruthy();
  expect(
    tree.root.findAllByProps({ accessibilityLabel: "banana.ui.retry" }),
  ).toHaveLength(0);
});

test("accepted Banana disease triggers recommendation lookup and renders its result", async () => {
  mockPredictBanana.mockResolvedValueOnce(basePrediction);
  mockLoadDiseaseRecommendation.mockResolvedValueOnce(
    recommendation("Cordana leaf spot", "Inspect nearby plants."),
  );

  const tree = await renderConfirmedBanana();

  expect(mockPredictBanana).toHaveBeenCalledTimes(1);
  expect(mockPredictBanana).toHaveBeenCalledWith(
    { uri: "file://banana.jpg", mimeType: "image/jpeg" },
    "confirmed-token",
    undefined,
  );
  expect(mockLoadDiseaseRecommendation).toHaveBeenCalledWith(
    "banana",
    "banana__cordana_leaf_spot",
  );
  expect(tree.root.findByProps({ children: "Cordana leaf spot" })).toBeTruthy();
  expect(renderedTree(tree)).toContain("Inspect nearby plants.");
});

test("accepted healthy Banana uses the healthy registry result without disease advice", async () => {
  mockPredictBanana.mockResolvedValueOnce({
    ...basePrediction,
    result: {
      ...basePrediction.result,
      class_id: "banana__healthy",
      display_name_key: "banana.result.healthy",
    },
    healthy_gate: {
      predicted_class: "banana__healthy",
      confidence: 0.95,
      margin: 0.7,
      accepted: true,
    },
    disease_classifier: {
      predicted_class: null,
      confidence: 0,
      margin: 0,
      accepted: false,
      executed: false,
    },
    message_key: "banana.result.healthy",
  });
  mockLoadDiseaseRecommendation.mockResolvedValueOnce(
    recommendation(
      "Healthy banana plant",
      "Continue routine field observation; do not apply a treatment based only on this result.",
    ),
  );

  const tree = await renderConfirmedBanana();

  expect(mockLoadDiseaseRecommendation).toHaveBeenCalledWith(
    "banana",
    "banana__healthy",
  );
  expect(
    tree.root.findByProps({ children: "Healthy banana plant" }),
  ).toBeTruthy();
  expect(renderedTree(tree)).toContain(
    "Continue routine field observation; do not apply a treatment based only on this result.",
  );
  expect(renderedTree(tree)).not.toContain("Inspect nearby plants.");
});

test.each([
  ["banana__healthy", "banana.result.healthy"],
  ["banana__cordana_leaf_spot", "banana.result.cordana"],
  ["banana__pestalotiopsis_leaf_spot", "banana.result.pestalotiopsis"],
  ["banana__sigatoka_leaf_spot", "banana.result.sigatoka"],
])(
  "accepted class %s shows pending verification when no approved guidance exists",
  async (classId, messageKey) => {
    mockPredictBanana.mockResolvedValueOnce({
      ...basePrediction,
      result: {
        ...basePrediction.result,
        class_id: classId,
        display_name_key: messageKey,
      },
      message_key: messageKey,
    });
    mockLoadDiseaseRecommendation.mockResolvedValueOnce(null);

    const tree = await renderConfirmedBanana();

    expect(mockLoadDiseaseRecommendation).toHaveBeenCalledWith(
      "banana",
      classId,
    );
    expect(renderedTree(tree)).toContain(
      "banana.ui.treatmentPendingVerification",
    );
  },
);
