const mockPost = jest.fn();

jest.mock("@/services/apiClient", () => ({
  httpClient: { post: (...args: unknown[]) => mockPost(...args) },
}));

import {
  GROUNDNUT_MAX_UPLOAD_BYTES,
  getGroundnutTextGuidance,
  mapGroundnutTranscript,
  predictGroundnut,
  transcribeGroundnutSymptoms,
  validateGroundnutUpload,
} from "../groundnutApi";

beforeEach(() => jest.clearAllMocks());

test("accepts JPEG, PNG, and WebP within the upload limit", () => {
  for (const mimeType of ["image/jpeg", "image/png", "image/webp"]) {
    expect(validateGroundnutUpload({ mimeType, fileSize: 1024 })).toBeNull();
  }
});

test("rejects an invalid image type before upload", () => {
  expect(
    validateGroundnutUpload({ mimeType: "image/gif", fileSize: 1024 }),
  ).toBe("unsupported_type");
});

test("rejects an image larger than 8 MiB before upload", () => {
  expect(
    validateGroundnutUpload({
      mimeType: "image/jpeg",
      fileSize: GROUNDNUT_MAX_UPLOAD_BYTES + 1,
    }),
  ).toBe("too_large");
});

test("uploads authenticated multipart data to the Groundnut endpoint", async () => {
  const response = { status: "accepted" };
  mockPost.mockResolvedValueOnce({ data: response });
  await expect(
    predictGroundnut({
      uri: "file://leaf.jpg",
      mimeType: "image/jpeg",
      fileSize: 1000,
    }),
  ).resolves.toBe(response);

  expect(mockPost).toHaveBeenCalledWith(
    "/doctor/groundnut/predict",
    expect.any(FormData),
    expect.objectContaining({ _skipRetry: true }),
  );
  const form = mockPost.mock.calls[0][1] as FormData;
  expect(form).toBeInstanceOf(FormData);
  expect(form.has("image")).toBe(true);
});

test("posts validated text symptoms to the Groundnut guidance endpoint", async () => {
  const response = { status: "preliminary_guidance" };
  mockPost.mockResolvedValueOnce({ data: response });
  await expect(getGroundnutTextGuidance(["dark_leaf_spots"])).resolves.toBe(response);
  expect(mockPost).toHaveBeenCalledWith(
    "/doctor/groundnut/symptoms",
    { symptoms: ["dark_leaf_spots"] },
    expect.objectContaining({ _skipRetry: true }),
  );
});

test("uploads voice audio and maps the returned transcript through authenticated APIs", async () => {
  mockPost
    .mockResolvedValueOnce({ data: { transcript: "Dark leaf spots" } })
    .mockResolvedValueOnce({
      data: { matched_symptoms: ["dark_leaf_spots"], unmatched_text: [], ambiguous_text: [] },
    });
  await expect(
    transcribeGroundnutSymptoms("file://voice.amr", "audio/amr", "en-IN"),
  ).resolves.toEqual({ transcript: "Dark leaf spots" });
  await expect(mapGroundnutTranscript("Dark leaf spots", "en-IN")).resolves.toEqual({
    matched_symptoms: ["dark_leaf_spots"], unmatched_text: [], ambiguous_text: [],
  });
  expect(mockPost.mock.calls[0][0]).toBe("/doctor/groundnut/transcribe");
  expect(mockPost.mock.calls[1][0]).toBe("/doctor/groundnut/symptoms/map-transcript");
});
