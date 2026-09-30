import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { StyleSheet } from "react-native";

const mockReplace = jest.fn();
const mockSetLanguage = jest.fn(() => Promise.resolve());
const mockConfirmLanguageSelection = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ replace: mockReplace }),
}));
jest.mock("expo-image", () => ({ Image: "Image" }));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock("@/hooks/useLanguage", () => ({
  useLanguage: () => ({ language: "ta", setLanguage: mockSetLanguage }),
}));
jest.mock("../store/authStore", () => ({
  useAuthStore: (
    selector: (state: { confirmLanguageSelection: () => void }) => unknown,
  ) => selector({ confirmLanguageSelection: mockConfirmLanguageSelection }),
}));

import { LanguageSelectScreen } from "../screens/LanguageSelectScreen";

describe("LanguageSelectScreen physical-layout regression", () => {
  beforeEach(() => jest.clearAllMocks());

  it("uses the AgrowNex brand name on the language-selection header", () => {
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(<LanguageSelectScreen />);
    });

    expect(
      tree.root.findByProps({
        accessibilityLabel: "language.tagline, AgrowNex",
      }),
    ).toBeTruthy();
    expect(
      tree.root.findAll((node) => node.children.includes("Agrow")),
    ).toHaveLength(1);
    expect(
      tree.root.findAll((node) => node.children.includes("Nex")),
    ).toHaveLength(1);
    expect(
      tree.root.findAll((node) => node.children.includes("AI")),
    ).toHaveLength(0);
  });

  it("keeps both languages in full-width selectable cards with contained indicators", () => {
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(<LanguageSelectScreen />);
    });

    for (const language of ["ta", "en"]) {
      const card = tree.root.findByProps({
        testID: `language-option-${language}`,
      });
      expect(card.props.accessibilityRole).toBe("radio");
      expect(typeof card.props.style).not.toBe("function");
      expect(StyleSheet.flatten(card.props.style).width).toBe("100%");
      expect(
        card.findByProps({ testID: `language-indicator-${language}` }),
      ).toBeTruthy();
    }
  });

  it("enables Continue for Tamil and English and preserves confirmation navigation", async () => {
    let tree!: TestRenderer.ReactTestRenderer;
    await act(async () => {
      tree = TestRenderer.create(<LanguageSelectScreen />);
    });

    const tamil = tree.root.findByProps({ testID: "language-option-ta" });
    const english = tree.root.findByProps({ testID: "language-option-en" });
    const continueButton = tree.root.findByProps({
      testID: "language-continue",
    });

    expect(tamil.props.accessibilityState).toMatchObject({
      checked: true,
      selected: true,
    });
    expect(continueButton.props.accessibilityState).toEqual({
      disabled: false,
    });
    expect(StyleSheet.flatten(continueButton.props.style)).toMatchObject({
      width: "100%",
      minHeight: 58,
      backgroundColor: "#78DB50",
      opacity: 1,
    });
    expect(typeof continueButton.props.style).not.toBe("function");

    await act(async () => {
      await english.props.onPress();
    });
    expect(
      tree.root.findByProps({ testID: "language-option-en" }).props
        .accessibilityState,
    ).toMatchObject({ checked: true, selected: true });
    expect(mockSetLanguage).toHaveBeenCalledWith("en");
    expect(
      tree.root.findByProps({ testID: "language-continue" }).props
        .accessibilityState,
    ).toEqual({ disabled: false });

    act(() => {
      tree.root.findByProps({ testID: "language-continue" }).props.onPress();
    });
    expect(mockConfirmLanguageSelection).toHaveBeenCalledTimes(1);
    expect(mockReplace).toHaveBeenCalledWith("/(auth)/login");
  });

  it("recovers from a language persistence failure without navigating", async () => {
    mockSetLanguage.mockRejectedValueOnce(new Error("storage unavailable"));
    let tree!: TestRenderer.ReactTestRenderer;
    await act(async () => {
      tree = TestRenderer.create(<LanguageSelectScreen />);
    });

    await act(async () => {
      await tree.root
        .findByProps({ testID: "language-option-en" })
        .props.onPress();
    });

    expect(
      tree.root.findByProps({ testID: "language-option-ta" }).props
        .accessibilityState,
    ).toMatchObject({ checked: true, selected: true });
    expect(tree.root.findByProps({ accessibilityRole: "alert" })).toBeTruthy();
    expect(mockReplace).not.toHaveBeenCalled();
    expect(
      tree.root.findByProps({ testID: "language-continue" }).props
        .accessibilityState,
    ).toEqual({ disabled: false });
  });
});
