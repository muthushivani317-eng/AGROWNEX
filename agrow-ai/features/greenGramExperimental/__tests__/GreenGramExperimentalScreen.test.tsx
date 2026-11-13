const mockReact = require("react");
const TestRenderer = require("react-test-renderer");
const mockPredict = jest.fn();
const mockGallery = jest.fn();
const mockTranslations: Record<string, string> = {
  "greenGram.title": "Green Gram — Experimental Test", "greenGram.subtitle": "Three-class research model",
  "greenGram.experimental": "Experimental research model", "greenGram.selectedImage": "Selected Green Gram leaf photograph",
  "greenGram.replaceImage": "Replace image", "greenGram.introTitle": "Photograph one Green Gram leaf",
  "greenGram.introBody": "Use a clear image", "greenGram.camera": "Take photo", "greenGram.gallery": "Choose from gallery",
  "greenGram.analyze": "Analyze leaf", "greenGram.analyzing": "Analyzing leaf…", "greenGram.resultTitle": "Experimental result",
  "greenGram.confidenceLabel": "Model confidence", "greenGram.topPredictions": "Ranked predictions", "greenGram.reviewRequired": "Expert review is required.",
  "greenGram.retry": "Try another photograph", "greenGram.diseases.healthy.name": "Healthy", "greenGram.diseases.leafCurl.name": "Leaf Curl",
  "greenGram.diseases.yellowMosaic.name": "Yellow Mosaic", "greenGram.errors.unsupported_type": "Choose a JPEG, PNG, or WebP image.",
};

jest.mock("expo-image", () => ({ Image: "Image" }));
jest.mock("lucide-react-native", () => { const { View } = require("react-native"); return new Proxy({}, { get: () => View }); });
jest.mock("@/hooks/useAppTheme", () => ({ useAppTheme: () => ({ colors: { primary: "#176b38", warning: "#a60", danger: "#b00", onPrimary: "#fff" } }) }));
jest.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => mockTranslations[key] ?? key }) }));
jest.mock("@/components/ui", () => { const { Pressable, Text, View } = require("react-native"); return { AgScreen: View, AgCard: View, AgText: Text, AgButton: ({ title, onPress, disabled, loading }: any) => mockReact.createElement(Pressable, { accessibilityLabel: title, onPress, disabled, loading }) }; });
jest.mock("@/features/disease/utils/pickDiseaseImage", () => ({ captureFromCamera: jest.fn(), pickFromGallery: (...args: unknown[]) => mockGallery(...args) }));
jest.mock("../greenGramApi", () => { const actual = jest.requireActual("../greenGramApi"); return { ...actual, GREEN_GRAM_PREDICTION_ENABLED: true, predictGreenGram: (...args: unknown[]) => mockPredict(...args) }; });

import { GreenGramUnavailableScreen } from "../GreenGramUnavailableScreen";

const image = { uri: "file://mung.jpg", mimeType: "image/jpeg", width: 500, height: 500, fileSize: 1000 };
const response = { crop: "green_gram", model_version: "green-gram-mendeley-3class-b0-exploratory-v1", status: "EXPERIMENTAL_RESULT", predicted_class: "mymv", confidence: 0.932, top_three_predictions: [{ class_id: "mymv", confidence: 0.932 }, { class_id: "healthy", confidence: 0.05 }, { class_id: "leaf_curl", confidence: 0.018 }], supported_classes: ["healthy", "leaf_curl", "mymv"], experimental: true, expert_review_required: true, experimental_notice: "Research only" };

async function render(initialImage: any = image) { let tree: any; await TestRenderer.act(async () => { tree = TestRenderer.create(mockReact.createElement(GreenGramUnavailableScreen, { initialImage })); }); return tree; }
beforeEach(() => jest.clearAllMocks());

test("shows preview, loading, real response fields and retry", async () => {
  let resolve!: (value: any) => void; mockPredict.mockReturnValueOnce(new Promise((done) => { resolve = done; }));
  const tree = await render();
  expect(tree.root.findByProps({ accessibilityLabel: "Selected Green Gram leaf photograph" })).toBeTruthy();
  await TestRenderer.act(async () => { tree.root.findByProps({ accessibilityLabel: "Analyze leaf" }).props.onPress(); await Promise.resolve(); });
  expect(tree.root.findByProps({ accessibilityRole: "progressbar" })).toBeTruthy();
  await TestRenderer.act(async () => resolve(response));
  const text = JSON.stringify(tree.toJSON());
  expect(text).toContain("Yellow Mosaic"); expect(text).toContain("93.2"); expect(text).toContain("Leaf Curl"); expect(text).toContain("green-gram-mendeley-3class-b0-exploratory-v1");
  expect(tree.root.findByProps({ accessibilityLabel: "Try another photograph" })).toBeTruthy();
});

test("gallery selection creates a preview and replacement clears it", async () => {
  mockGallery.mockResolvedValueOnce(image); const tree = await render(null);
  await TestRenderer.act(async () => { await tree.root.findByProps({ accessibilityLabel: "Choose from gallery" }).props.onPress(); });
  expect(tree.root.findByProps({ accessibilityLabel: "Selected Green Gram leaf photograph" })).toBeTruthy();
  await TestRenderer.act(async () => tree.root.findByProps({ accessibilityLabel: "Replace image" }).props.onPress());
  expect(tree.root.findAllByProps({ accessibilityLabel: "Selected Green Gram leaf photograph" })).toHaveLength(0);
});

test("rejects an invalid gallery file before prediction", async () => {
  mockGallery.mockResolvedValueOnce({ ...image, mimeType: "image/gif" }); const tree = await render(null);
  await TestRenderer.act(async () => { await tree.root.findByProps({ accessibilityLabel: "Choose from gallery" }).props.onPress(); });
  expect(JSON.stringify(tree.toJSON())).toContain("Choose a JPEG, PNG, or WebP image"); expect(mockPredict).not.toHaveBeenCalled();
});
