const mockReact = require("react");
const TestRenderer = require("react-test-renderer");

const mockPredictGroundnut = jest.fn();
const mockGetGroundnutTextGuidance = jest.fn();
const mockTranscribeGroundnutSymptoms = jest.fn();
const mockMapGroundnutTranscript = jest.fn();
const mockSubmitGroundnutPestObservation = jest.fn();
const mockPickGallery = jest.fn();

jest.mock("react-i18next", () => ({
  useTranslation: () => {
    const { en } = jest.requireActual("@/localization/locales/en");
    return {
      i18n: { language: "en" },
      t: (key: string, options?: { defaultValue?: string }) =>
        key.split(".").reduce((value: any, part) => value?.[part], en) ??
        options?.defaultValue ??
        key,
    };
  },
}));
jest.mock("expo-image", () => ({ Image: "Image" }));
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({
    colors: {
      primary: "#176b38",
      warning: "#a66000",
      danger: "#b42318",
      onPrimary: "#fff",
      border: "#ddd",
      textMuted: "#666",
    },
  }),
}));
jest.mock("@/hooks/useLanguage", () => ({
  useLanguage: () => ({ language: "en", isTamil: false }),
}));
jest.mock("@/components/ui", () => {
  const { Pressable, Text, View } = require("react-native");
  return {
    AgScreen: View,
    AgCard: View,
    AgText: Text,
    AgButton: ({
      title,
      onPress,
      disabled,
      loading,
      accessibilityLabel,
    }: any) =>
      mockReact.createElement(Pressable, {
        accessibilityLabel: accessibilityLabel ?? title,
        onPress,
        disabled,
        loading,
      }),
  };
});
jest.mock("@/features/disease/utils/pickDiseaseImage", () => ({
  captureFromCamera: jest.fn(),
  pickFromGallery: (...args: unknown[]) => mockPickGallery(...args),
}));
jest.mock("@/features/dailyFarmTask/components/VoiceNoteRecorder", () => {
  const { Pressable } = require("react-native");
  return {
    GROUNDNUT_SPEECH_RECORDING_OPTIONS: {},
    VoiceNoteRecorder: ({ onRecorded, labels }: any) =>
      mockReact.createElement(Pressable, {
        accessibilityLabel: labels.start,
        onPress: () => onRecorded("file://voice.amr"),
      }),
  };
});
jest.mock("../groundnutApi", () => {
  const actual = jest.requireActual("../groundnutApi");
  return {
    ...actual,
    predictGroundnut: (...args: unknown[]) => mockPredictGroundnut(...args),
    getGroundnutTextGuidance: (...args: unknown[]) => mockGetGroundnutTextGuidance(...args),
    transcribeGroundnutSymptoms: (...args: unknown[]) => mockTranscribeGroundnutSymptoms(...args),
    mapGroundnutTranscript: (...args: unknown[]) => mockMapGroundnutTranscript(...args),
    submitGroundnutPestObservation: (...args: unknown[]) =>
      mockSubmitGroundnutPestObservation(...args),
  };
});

import { GroundnutDiseaseDetectionScreen } from "../screens/GroundnutDiseaseDetectionScreen";

const image = {
  uri: "file://groundnut.jpg",
  base64: "",
  mimeType: "image/jpeg",
  width: 1000,
  height: 1000,
  fileSize: 100_000,
};

const quality = {
  status: "accepted",
  reasons: [],
  width: 1000,
  height: 1000,
  brightness: 100,
  contrast: 30,
  blur_score: 50,
};

const top = [
  { class_id: "rust", display_name: "Rust", confidence: 0.96 },
  {
    class_id: "early_leaf_spot",
    display_name: "Early Leaf Spot",
    confidence: 0.02,
  },
  { class_id: "healthy_leaf", display_name: "Healthy Leaf", confidence: 0.01 },
];

const accepted = {
  request_id: "request-1",
  crop: "groundnut",
  model_version: "groundnut-efficientnet-b2-v1",
  experimental: true,
  experimental_notice: "Experimental",
  status: "accepted",
  predicted_disease: top[0],
  confidence_category: "HIGH",
  confidence_score: 0.96,
  top_three_predictions: top,
  candidate_prediction: top[0],
  image_quality: quality,
  rejection_reasons: [],
  expert_review_required: false,
  runtime_device: "cpu",
  processing_time_ms: 100,
};

async function renderWithImage() {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(GroundnutDiseaseDetectionScreen, {
        initialImage: image,
      }),
    );
  });
  return tree;
}

async function analyze(tree: any) {
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Analyze Groundnut leaf" })
      .props.onPress();
    await Promise.resolve();
  });
}

beforeEach(() => jest.clearAllMocks());

test("selects Groundnut symptoms and displays preliminary expert-review guidance", async () => {
  mockGetGroundnutTextGuidance.mockResolvedValueOnce({
    crop: "groundnut",
    status: "preliminary_guidance",
    observed_symptoms: ["dark_leaf_spots"],
    possible_patterns: ["leaf_spot_pattern"],
    guidance: "These observations can have multiple causes.",
    expert_review_required: true,
    confirmed_disease: null,
    image_model_confidence: null,
    warnings: ["This response is preliminary guidance, not a diagnosis."],
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(GroundnutDiseaseDetectionScreen));
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: "Dark leaf spots" }).props.onPress();
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: "Check selected symptoms" }).props.onPress();
    await Promise.resolve();
  });
  expect(mockGetGroundnutTextGuidance).toHaveBeenCalledWith(["dark_leaf_spots"]);
  const rendered = JSON.stringify(tree.toJSON());
  expect(rendered).toContain("Preliminary symptom guidance");
  expect(rendered).toContain("Expert review is required");
  expect(rendered).not.toContain("Confidence");
});

test("requires farmer confirmation before voice suggestions become selected symptoms", async () => {
  mockTranscribeGroundnutSymptoms.mockResolvedValueOnce({ transcript: "Dark leaf spots. Unsure text." });
  mockMapGroundnutTranscript.mockResolvedValueOnce({
    matched_symptoms: ["dark_leaf_spots"],
    unmatched_text: ["Unsure text"],
    ambiguous_text: ["Maybe light leaf spots"],
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(GroundnutDiseaseDetectionScreen));
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: "Record symptom voice note" }).props.onPress();
  });
  const review = JSON.stringify(tree.toJSON());
  expect(review).toContain("Dark leaf spots. Unsure text.");
  expect(review).toContain("Unsure text");
  expect(review).toContain("Maybe light leaf spots");
  expect(
    tree.root.findByProps({ accessibilityLabel: "Dark leaf spots" }).props.accessibilityState.checked,
  ).toBe(false);
  expect(mockGetGroundnutTextGuidance).not.toHaveBeenCalled();

  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Confirm and add suggested symptoms" })
      .props.onPress();
  });
  expect(
    tree.root.findByProps({ accessibilityLabel: "Dark leaf spots" }).props.accessibilityState.checked,
  ).toBe(true);
  expect(mockGetGroundnutTextGuidance).not.toHaveBeenCalled();
});

test("shows a clear localized text-symptom validation error", async () => {
  mockGetGroundnutTextGuidance.mockRejectedValueOnce({ status: 422 });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(GroundnutDiseaseDetectionScreen));
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: "Dark leaf spots" }).props.onPress();
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: "Check selected symptoms" }).props.onPress();
    await Promise.resolve();
  });
  expect(JSON.stringify(tree.toJSON())).toContain(
    "One or more symptoms could not be accepted",
  );
});

test("shows a clear localized voice service-unavailable error", async () => {
  mockTranscribeGroundnutSymptoms.mockRejectedValueOnce({ status: 503 });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(mockReact.createElement(GroundnutDiseaseDetectionScreen));
  });
  await TestRenderer.act(async () => {
    await tree.root.findByProps({ accessibilityLabel: "Record symptom voice note" }).props.onPress();
  });
  expect(JSON.stringify(tree.toJSON())).toContain(
    "Voice transcription is temporarily unavailable",
  );
});

test("shows the selected image preview and lets the tester replace it", async () => {
  const tree = await renderWithImage();
  expect(
    tree.root.findByProps({
      accessibilityLabel: "Selected Groundnut leaf photograph",
    }),
  ).toBeTruthy();
  expect(
    tree.root.findByProps({ accessibilityLabel: "Replace image" }),
  ).toBeTruthy();
});

test("offers the optional growth-stage action without replacing disease analysis", async () => {
  const onCheckGrowthStage = jest.fn();
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(GroundnutDiseaseDetectionScreen, {
        initialImage: image,
        onCheckGrowthStage,
      }),
    );
  });

  tree.root
    .findByProps({ accessibilityLabel: "Check Growth Stage" })
    .props.onPress();
  expect(onCheckGrowthStage).toHaveBeenCalledTimes(1);
  expect(
    tree.root.findByProps({ accessibilityLabel: "Analyze Groundnut leaf" }),
  ).toBeTruthy();
});

test("shows a loading state while the backend analyzes the leaf", async () => {
  let resolve!: (value: typeof accepted) => void;
  mockPredictGroundnut.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const tree = await renderWithImage();
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Analyze Groundnut leaf" })
      .props.onPress();
    await Promise.resolve();
  });
  expect(
    tree.root.findByProps({ accessibilityRole: "progressbar" }),
  ).toBeTruthy();
  await TestRenderer.act(async () => resolve(accepted));
});

test("renders an accepted result as likely, with confidence and top three", async () => {
  mockPredictGroundnut.mockResolvedValueOnce(accepted);
  const tree = await renderWithImage();
  await analyze(tree);
  const rendered = JSON.stringify(tree.toJSON());
  expect(rendered).toContain("Likely classification");
  expect(rendered).toContain("Rust");
  expect(rendered).toContain("96.0%");
  expect(rendered).toContain("HIGH");
  expect(rendered).toContain("Early Leaf Spot");
  expect(rendered).toContain("Healthy Leaf");
  expect(rendered).toContain("groundnut-efficientnet-b2-v1");
});

test("requires explicit consent and submits the selected photo as a pending pest observation", async () => {
  mockPredictGroundnut.mockResolvedValueOnce(accepted);
  mockSubmitGroundnutPestObservation.mockResolvedValueOnce({
    observation_id: "observation-1",
    crop: "groundnut",
    status: "pending_expert_review",
    damage_extent: "several",
    spread_speed: "rapid",
    consent: true,
    private_photo_stored: true,
    pest_label: null,
    diagnosis: null,
  });
  const tree = await renderWithImage();
  await analyze(tree);

  await TestRenderer.act(async () => {
    tree.root.findByProps({ accessibilityLabel: "Several plants or patches" }).props.onPress();
    tree.root.findByProps({ accessibilityLabel: "Yes, spreading rapidly" }).props.onPress();
  });
  const submit = tree.root.findByProps({
    accessibilityLabel: "Submit Groundnut pest observation for expert review",
  });
  expect(submit.props.disabled).toBe(true);
  await TestRenderer.act(async () => {
    submit.props.onPress();
    await Promise.resolve();
  });
  expect(mockSubmitGroundnutPestObservation).not.toHaveBeenCalled();

  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Consent to private photo expert review" })
      .props.onPress();
  });
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Submit Groundnut pest observation for expert review" })
      .props.onPress();
    await Promise.resolve();
  });

  expect(mockSubmitGroundnutPestObservation).toHaveBeenCalledWith(image, {
    damageExtent: "several",
    spreadSpeed: "rapid",
    consent: true,
    captureMethod: "gallery",
  });
  const pending = tree.root.findByProps({ testID: "groundnut-pest-review-pending" });
  const pendingText = pending
    .findAllByType(require("react-native").Text)
    .flatMap((node: any) => node.props.children)
    .join(" ");
  expect(pendingText).toContain("pending expert review");
  expect(pendingText).toContain("No pest has been identified");
  expect(pendingText.toLowerCase()).not.toContain("confidence");
});

test("renders review-required candidate as possible and requests expert review", async () => {
  mockPredictGroundnut.mockResolvedValueOnce({
    ...accepted,
    status: "review_required",
    predicted_disease: null,
    confidence_category: "MEDIUM",
    expert_review_required: true,
    rejection_reasons: ["EXPERT_REVIEW_REQUIRED"],
  });
  const tree = await renderWithImage();
  await analyze(tree);
  const rendered = JSON.stringify(tree.toJSON());
  expect(rendered).toContain("Possible classification");
  expect(rendered).toContain("Expert review required");
  expect(rendered).not.toContain("Likely classification");
});

test("renders a rejected photograph without a disease classification", async () => {
  mockPredictGroundnut.mockResolvedValueOnce({
    ...accepted,
    status: "rejected",
    predicted_disease: null,
    candidate_prediction: null,
    confidence_category: null,
    confidence_score: null,
    top_three_predictions: [],
    image_quality: {
      ...quality,
      status: "rejected",
      reasons: ["IMAGE_TOO_BLURRY"],
    },
    rejection_reasons: ["IMAGE_TOO_BLURRY"],
  });
  const tree = await renderWithImage();
  await analyze(tree);
  const rendered = JSON.stringify(tree.toJSON());
  expect(rendered).toContain("Photograph not accepted");
  expect(rendered).toContain("Hold the camera steady");
  expect(rendered).not.toContain("Likely classification");
  expect(
    tree.root.findByProps({ accessibilityLabel: "Analyze another photograph" }),
  ).toBeTruthy();
});

test("invalid gallery image is blocked before prediction", async () => {
  mockPickGallery.mockResolvedValueOnce({ ...image, mimeType: "image/gif" });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(GroundnutDiseaseDetectionScreen),
    );
  });
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Choose from gallery" })
      .props.onPress();
    await Promise.resolve();
  });
  expect(JSON.stringify(tree.toJSON())).toContain("JPEG, PNG, or WebP");
  expect(mockPredictGroundnut).not.toHaveBeenCalled();
});

test("oversized gallery image is blocked before prediction", async () => {
  mockPickGallery.mockResolvedValueOnce({
    ...image,
    fileSize: 8 * 1024 * 1024 + 1,
  });
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      mockReact.createElement(GroundnutDiseaseDetectionScreen),
    );
  });
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ accessibilityLabel: "Choose from gallery" })
      .props.onPress();
    await Promise.resolve();
  });
  expect(JSON.stringify(tree.toJSON())).toContain("8 MiB");
  expect(mockPredictGroundnut).not.toHaveBeenCalled();
});

test("allows a manual retry after a network failure", async () => {
  mockPredictGroundnut
    .mockRejectedValueOnce({ status: 0 })
    .mockResolvedValueOnce(accepted);
  const tree = await renderWithImage();
  await analyze(tree);
  expect(JSON.stringify(tree.toJSON())).toContain("temporarily unavailable");

  await analyze(tree);
  expect(JSON.stringify(tree.toJSON())).toContain("Likely classification");
  expect(mockPredictGroundnut).toHaveBeenCalledTimes(2);
});
