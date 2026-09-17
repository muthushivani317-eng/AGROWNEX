export function cropConfirmationCopy(input: {
  cropId: string;
  cropName: string;
  suggestedCropId?: string | null;
  suggestedCropName?: string | null;
  identificationConfidence?: number | null;
}): { key: string; params: Record<string, string | number> } {
  if (input.suggestedCropId === input.cropId) {
    if (!Number.isFinite(input.identificationConfidence)) {
      return {
        key: "disease.cropConfirmationAiMatchConfidenceUnavailable",
        params: { crop: input.cropName },
      };
    }
    return {
      key: "disease.cropConfirmationAiMatch",
      params: {
        crop: input.cropName,
        confidence: Math.round((input.identificationConfidence as number) * 100),
      },
    };
  }
  if (input.suggestedCropId) {
    return {
      key: "disease.cropConfirmationAiCorrection",
      params: {
        crop: input.cropName,
        suggestedCrop: input.suggestedCropName ?? input.suggestedCropId,
      },
    };
  }
  return {
    key: "disease.cropConfirmationManual",
    params: { crop: input.cropName },
  };
}
