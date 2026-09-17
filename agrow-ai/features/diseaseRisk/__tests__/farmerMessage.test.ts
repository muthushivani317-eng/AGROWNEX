import { en } from "@/localization/locales/en";
import { ta } from "@/localization/locales/ta";

import {
  farmerMessageOrFallback,
  KNOWN_FARMER_MESSAGE_KEYS,
} from "../types";

describe("disease-risk farmer_message_key translation coverage", () => {
  it("has a real (non-empty) translation for every backend-emitted key in both locales", () => {
    for (const key of KNOWN_FARMER_MESSAGE_KEYS) {
      const leaf = key.split(".")[1] as keyof typeof en.diseaseRisk;
      expect(en.diseaseRisk[leaf]).toBeTruthy();
      expect(ta.diseaseRisk[leaf]).toBeTruthy();
    }
  });
});

describe("farmerMessageOrFallback", () => {
  it("returns the real translation when the key is recognised", () => {
    const translate = (key: string) =>
      key === "diseaseRisk.conditionsPresent" ? "translated copy" : key;
    expect(farmerMessageOrFallback("diseaseRisk.conditionsPresent", translate)).toBe(
      "translated copy",
    );
  });

  it("never renders a raw i18n key to the farmer -- falls back to safe copy instead", () => {
    // Simulates react-i18next's default behaviour of echoing back an unknown key.
    const translateMissingKey = (key: string) => key;
    const result = farmerMessageOrFallback(
      "diseaseRisk.someFutureKeyNotYetTranslated",
      translateMissingKey,
    );
    expect(result).not.toBe("diseaseRisk.someFutureKeyNotYetTranslated");
    expect(result).toBe(en.diseaseRisk.noVerifiedRule);
  });
});
