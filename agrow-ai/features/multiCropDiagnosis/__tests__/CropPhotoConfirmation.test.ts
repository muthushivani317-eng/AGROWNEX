import { cropConfirmationCopy } from "../cropConfirmationCopy";

describe("crop confirmation copy classification", () => {
  test("uses AI-match copy when the farmer accepts the AI suggestion", () => {
    expect(
      cropConfirmationCopy({
        cropId: "banana",
        cropName: "Banana",
        suggestedCropId: "banana",
        suggestedCropName: "Banana",
        identificationConfidence: 0.96,
      }),
    ).toEqual({
      key: "disease.cropConfirmationAiMatch",
      params: { crop: "Banana", confidence: 96 },
    });
  });

  test("uses correction copy when the farmer overrides the AI suggestion", () => {
    expect(
      cropConfirmationCopy({
        cropId: "groundnut",
        cropName: "Groundnut",
        suggestedCropId: "paddy",
        suggestedCropName: "Paddy",
        identificationConfidence: 0.64,
      }),
    ).toEqual({
      key: "disease.cropConfirmationAiCorrection",
      params: { crop: "Groundnut", suggestedCrop: "Paddy" },
    });
  });

  test.each([undefined, Number.NaN, Number.POSITIVE_INFINITY])(
    "uses confidence-unavailable copy for invalid AI confidence %p",
    (identificationConfidence) => {
      expect(
        cropConfirmationCopy({
          cropId: "banana",
          cropName: "Banana",
          suggestedCropId: "banana",
          suggestedCropName: "Banana",
          identificationConfidence,
        }),
      ).toEqual({
        key: "disease.cropConfirmationAiMatchConfidenceUnavailable",
        params: { crop: "Banana" },
      });
    },
  );

  test("uses manual copy when AI returned no suggestion", () => {
    expect(
      cropConfirmationCopy({
        cropId: "cotton",
        cropName: "Cotton",
        suggestedCropId: null,
      }),
    ).toEqual({
      key: "disease.cropConfirmationManual",
      params: { crop: "Cotton" },
    });
  });
});
