const mockPost = jest.fn();

jest.mock("@/services/apiClient", () => ({ httpClient: { post: mockPost } }));

import { GREEN_GRAM_PREDICTION_ENABLED, predictGreenGram } from "../greenGramApi";

test("Green Gram prediction is compile-time disabled and makes no request", async () => {
  expect(GREEN_GRAM_PREDICTION_ENABLED).toBe(false);
  await expect(
    predictGreenGram({ uri: "file://leaf.jpg", mimeType: "image/jpeg" }),
  ).rejects.toThrow("green_gram_model_not_available");
  expect(mockPost).not.toHaveBeenCalled();
});
