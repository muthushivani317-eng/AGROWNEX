const mockPost = jest.fn();
jest.mock("@/services/apiClient", () => ({ httpClient: { post: (...args: unknown[]) => mockPost(...args) } }));

beforeAll(() => { process.env.EXPO_PUBLIC_GREEN_GRAM_EXPERIMENTAL_ENABLED = "true"; });
beforeEach(() => jest.clearAllMocks());

test("validates the three supported upload formats and size", () => {
  jest.resetModules();
  const api = require("../greenGramApi");
  for (const mimeType of ["image/jpeg", "image/png", "image/webp"]) expect(api.validateGreenGramUpload({ mimeType, fileSize: 10 })).toBeNull();
  expect(api.validateGreenGramUpload({ mimeType: "image/gif", fileSize: 10 })).toBe("unsupported_type");
  expect(api.validateGreenGramUpload({ mimeType: "image/jpeg", fileSize: api.GREEN_GRAM_MAX_UPLOAD_BYTES + 1 })).toBe("too_large");
});

test("uploads multipart data to the separate experimental endpoint", async () => {
  jest.resetModules();
  const api = require("../greenGramApi");
  const result = { experimental: true, predicted_class: "mymv" };
  mockPost.mockResolvedValueOnce({ data: result });
  await expect(api.predictGreenGram({ uri: "file://leaf.jpg", mimeType: "image/jpeg", fileSize: 10 })).resolves.toBe(result);
  expect(mockPost).toHaveBeenCalledWith("/doctor/green-gram/predict", expect.any(FormData), expect.objectContaining({ _skipRetry: true }));
});
