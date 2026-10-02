const React = require("react");
const TestRenderer = require("react-test-renderer");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { crop?: string; confidence?: number }) =>
      options?.crop
        ? `${key}:${options.crop}`
        : options?.confidence != null
          ? `${options.confidence}%`
          : key,
  }),
}));
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({
    colors: {
      primary: "#4CAF50",
      primaryLight: "#81C784",
      primaryDark: "#2E7D32",
      warning: "#FFCA28",
      danger: "#EF5350",
      card: "#252525",
      surface: "#1E1E1E",
      border: "#333333",
      text: "#FFFFFF",
      textMuted: "#BDBDBD",
      onPrimary: "#0C140F",
    },
  }),
}));
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});
jest.mock("@/components/ui", () => {
  const { Text } = require("react-native");
  return { AgText: Text };
});

import fs from "node:fs";
import path from "node:path";
import { Linking } from "react-native";

import { RecommendationResultCard } from "../components/RecommendationResultCard";
import { CropPhotoConfirmation } from "@/features/multiCropDiagnosis/components/CropPhotoConfirmation";

const bananaScreen = fs.readFileSync(
  path.resolve(
    __dirname,
    "..",
    "..",
    "bananaV3",
    "screens",
    "BananaDiseaseDetectionScreen.tsx",
  ),
  "utf8",
);
const bananaResult = fs.readFileSync(
  path.resolve(
    __dirname,
    "..",
    "..",
    "bananaV3",
    "components",
    "BananaPredictionResult.tsx",
  ),
  "utf8",
);

describe("Disease result redesign", () => {
  it("keeps crop confirmation and change/retake callbacks functional", async () => {
    const onConfirm = jest.fn();
    const onChangeCrop = jest.fn();
    const onRetake = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(CropPhotoConfirmation, {
          cropId: "banana",
          cropName: "Runtime Banana",
          confirmed: false,
          onConfirm,
          onChangeCrop,
          onRetake,
        }),
      );
    });
    await TestRenderer.act(async () =>
      tree.root
        .findAllByProps({
          accessibilityLabel: "disease.confirmCrop:Runtime Banana",
        })
        .find((node: any) => node.props.onPress)
        .props.onPress(),
    );
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(tree.toJSON())).toContain("Runtime Banana");
  });

  it("shows a readable chemical note (never the raw status) and official source links", async () => {
    const open = jest
      .spyOn(Linking, "openURL")
      .mockResolvedValueOnce(true as never);
    const recommendation = {
      canonical_disease_name_en: "Runtime disease",
      canonical_disease_name_ta: "நிகழ்நேர நோய்",
      why_it_occurs_en: ["Runtime cause"],
      why_it_occurs_ta: ["காரணம்"],
      symptoms_en: [],
      symptoms_ta: [],
      immediate_actions_en: [],
      immediate_actions_ta: [],
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
      agricultural_disclaimer: "Runtime screening disclaimer",
      official_sources: [
        { title: "Runtime official source", url: "https://example.gov/source" },
      ],
    };
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(RecommendationResultCard, {
          recommendation,
          language: "en",
        }),
      );
    });
    const output = JSON.stringify(tree.toJSON());
    expect(output).toContain("Runtime disease");
    expect(output).not.toContain("CHEMICAL_RECOMMENDATION_WITHHELD");
    expect(output).toContain("disease.chemicalWithheld");
    expect(output).toContain("Runtime screening disclaimer");
    const link = tree.root
      .findAllByProps({ accessibilityLabel: "Runtime official source" })
      .find((node: any) => node.props.onPress);
    await TestRenderer.act(async () => link.props.onPress());
    expect(open).toHaveBeenCalledWith("https://example.gov/source");
  });

  it("follows the organic chemical policy: category when allowed, hidden during conversion", async () => {
    const base = {
      canonical_disease_name_en: "Runtime disease",
      canonical_disease_name_ta: "நோய்",
      why_it_occurs_en: [], why_it_occurs_ta: [], symptoms_en: [], symptoms_ta: [],
      immediate_actions_en: [], immediate_actions_ta: [],
      cultural_management_en: ["Remove infected leaves"], cultural_management_ta: [],
      biological_options_en: [], biological_options_ta: [],
      nutrient_correction_en: [], nutrient_correction_ta: [],
      prevention_en: [], prevention_ta: [],
      escalation_conditions_en: [], escalation_conditions_ta: [],
      chemical_recommendation_status: "CHEMICAL_RECOMMENDATION_WITHHELD",
      conventional_category_en: "Fungicide category",
      conventional_category_ta: null,
      agricultural_disclaimer: "",
      official_sources: [],
    };
    const render = async (chemicalPolicy: string) => {
      let tree: any;
      await TestRenderer.act(async () => {
        tree = TestRenderer.create(
          React.createElement(RecommendationResultCard, {
            recommendation: base,
            language: "en",
            chemicalPolicy,
          }),
        );
      });
      return JSON.stringify(tree.toJSON());
    };
    const shown = await render("show");
    expect(shown).toContain("Fungicide category");
    expect(shown.indexOf("Remove infected leaves")).toBeLessThan(shown.indexOf("Fungicide category"));
    expect(await render("last_resort")).toContain("organic.chemicalLastResort");
    const hidden = await render("hide");
    expect(hidden).not.toContain("Fungicide category");
    expect(hidden).toContain("organic.chemicalNotAllowed");
  });

  it("keeps runtime image handlers and never hardcodes reference confidence or disease values", () => {
    expect(bananaScreen).toMatch(/pick\(["']camera["']\)/);
    expect(bananaScreen).toMatch(/pick\(["']gallery["']\)/);
    expect(bananaScreen).toContain("onPress={startFreshWorkflow}");
    expect(bananaScreen).toContain("onChangeCrop={onChangeCrop}");
    expect(bananaResult).toContain("response.result.confidence");
    expect(bananaResult).toContain("response.result.display_name_key");
    expect(bananaResult).not.toContain("92%");
    expect(bananaResult).not.toContain("Sigatoka");
  });
});
