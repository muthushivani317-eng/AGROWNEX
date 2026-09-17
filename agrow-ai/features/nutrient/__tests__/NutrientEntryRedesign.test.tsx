const React = require("react");
const TestRenderer = require("react-test-renderer");
const fs = require("fs");
const path = require("path");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({
    colors: {
      primary: "#4CAF50",
      card: "#252525",
      surface: "#1E1E1E",
      border: "#333333",
      text: "#FFFFFF",
      onPrimary: "#0C140F",
    },
  }),
}));
jest.mock("@/hooks/useLanguage", () => ({
  useLanguage: () => ({ language: "en" }),
}));
jest.mock("expo-router", () => ({
  useRouter: () => ({ back: jest.fn(), push: jest.fn() }),
  useLocalSearchParams: () => ({}),
}));
jest.mock("expo-image", () => ({ Image: require("react-native").View }));
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});
jest.mock("@/components/ui", () => {
  const { Text, View } = require("react-native");
  return {
    AgText: Text,
    AgButton: View,
    AgCard: View,
    AgOfflineBanner: View,
    AgScreen: View,
  };
});
jest.mock("@/features/disease", () => ({
  captureFromCamera: jest.fn(),
  pickFromGallery: jest.fn(),
  checkImageQuality: jest.fn(),
}));
jest.mock("@/features/weather", () => ({ useSelectedFarm: jest.fn() }));
jest.mock("@/features/weather/components/FarmSelector", () => ({
  FarmSelector: require("react-native").View,
}));
jest.mock("../hooks/useNutrient", () => ({ useAnalyzeNutrient: jest.fn() }));
jest.mock("../hooks/useNutrientSync", () => ({ useNutrientSync: jest.fn() }));

import { NutrientEntryState } from "../screens/NutrientAnalysisScreen";
import { ta } from "../../../localization/locales/ta";

test("entry actions invoke the existing camera and gallery callbacks", async () => {
  const onCamera = jest.fn();
  const onGallery = jest.fn();
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(NutrientEntryState, { onCamera, onGallery }),
    );
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ testID: "nutrient-take-photo" }).props.onPress();
  });
  await TestRenderer.act(async () => {
    tree.root
      .findByProps({ testID: "nutrient-choose-gallery" })
      .props.onPress();
  });
  expect(onCamera).toHaveBeenCalledTimes(1);
  expect(onGallery).toHaveBeenCalledTimes(1);
});

test("smart-analysis and neutral photo-tip localization are rendered", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(NutrientEntryState, {
        onCamera: jest.fn(),
        onGallery: jest.fn(),
      }),
    );
  });
  for (const key of [
    "nutrient.smartAnalysis",
    "nutrient.subtitle",
    "nutrient.tipsTitle",
    "nutrient.tipNaturalLight",
    "nutrient.tipWholeLeaf",
    "nutrient.tipFocus",
  ]) {
    expect(tree.root.findAllByProps({ children: key })).not.toHaveLength(0);
  }
  expect(ta.nutrient.smartAnalysis).toBeTruthy();
  expect(ta.nutrient.tipNaturalLight).toBeTruthy();
});

test("single route and original picker/analyze separation contracts remain intact", () => {
  const route = fs.readFileSync(
    path.join(process.cwd(), "app/nutrient/index.tsx"),
    "utf8",
  );
  const screen = fs.readFileSync(
    path.join(
      process.cwd(),
      "features/nutrient/screens/NutrientAnalysisScreen.tsx",
    ),
    "utf8",
  );
  const types = fs.readFileSync(
    path.join(process.cwd(), "features/nutrient/types.ts"),
    "utf8",
  );
  expect(route).toContain("NutrientAnalysisScreen");
  expect(screen).toMatch(
    /source === ["']camera["']\s*\? await captureFromCamera\(\)\s*: await pickFromGallery\(\)/,
  );
  expect(screen).toMatch(/routeContext\.source === ["']disease_detection["']/);
  expect(screen).toMatch(/onCamera=\{\(\) => void onPick\(["']camera["']\)\}/);
  expect(screen).toMatch(
    /onGallery=\{\(\) => void onPick\(["']gallery["']\)\}/,
  );
  expect(types).toContain("soilReference:");
  expect(types).toContain("satelliteReference:");
  expect(types).toContain("weatherReference:");
  expect(screen).not.toMatch(/92%|nitrogen deficiency|potassium deficiency/i);
});

test("light nutrient surfaces use fixed readable text across entry and results", () => {
  const files = [
    "screens/NutrientAnalysisScreen.tsx",
    "screens/NutrientHistoryScreen.tsx",
    "screens/NutrientResultScreen.tsx",
    "components/DeficiencyResultCard.tsx",
    "components/EvidenceCard.tsx",
    "components/NutrientRecommendationCard.tsx",
    "components/SymptomList.tsx",
    "components/ConfidenceMeter.tsx",
  ].map((file) =>
    fs.readFileSync(path.join(process.cwd(), "features/nutrient", file), "utf8"),
  );

  for (const source of files) {
    expect(source).not.toContain('color="muted"');
  }
  expect(files[0]).toContain("primaryText: { color: NUTRIENT_UI.text }");
  expect(files[0]).toContain("mutedText: { color: NUTRIENT_UI.muted }");
  expect(files[0]).toContain("<TouchableOpacity");
  expect(files[0]).toContain("{ backgroundColor: NUTRIENT_UI.chlorophyll }");
  expect(files[0]).not.toContain("style={({ pressed })");
  expect(files[1]).toContain("<AgEmptyState\n            light");
  expect(files[2]).toContain("<AgErrorState light");
});
