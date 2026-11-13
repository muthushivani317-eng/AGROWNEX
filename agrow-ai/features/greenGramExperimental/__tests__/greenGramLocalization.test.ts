import { en } from "@/localization/locales/en";
import { ml } from "@/localization/locales/ml";
import { ta } from "@/localization/locales/ta";
import { SUPPORTED_LANGUAGES } from "@/localization";

test("Malayalam is available through the persisted localization registry", () => {
  expect(SUPPORTED_LANGUAGES).toEqual(["ta", "en", "ml"]);
});

test.each([en.greenGram, ta.greenGram, ml.greenGram])("Green Gram locale separates experimental and five-class copy", (copy) => {
  expect(copy.title).toBeTruthy();
  expect(copy.camera).toBeTruthy();
  expect(copy.gallery).toBeTruthy();
  expect(copy.unavailableBody).toBeTruthy();
  expect(Object.keys(copy.diseases)).toEqual(["healthy", "yellowMosaic", "leafCurl", "leafCrinkle", "powderyMildew", "cercospora"]);
  expect(copy.experimental).toMatch(/Healthy|ஆரோக்கியமான|ആരോഗ്യമുള്ള/);
  for (const disease of Object.values(copy.diseases)) {
    expect(disease.name).toBeTruthy(); expect(disease.description).toBeTruthy(); expect(disease.guidance).toBeTruthy();
  }
});
