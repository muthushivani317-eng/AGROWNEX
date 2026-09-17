import {
  classifyCropDiagnosisFailure,
  parseCropDiagnosisResponse,
} from "../responseParser";

const accepted = {
  outcome: "accepted",
  crop_id: "rice",
  crop_identity_source: "user_confirmed_not_ai_verified",
  class_id: "rice_blast",
  qualitative_confidence: "high",
  calibrated_confidence: 0.87,
  accepted: true,
  official_accuracy_claim: false,
  field_validation_status: "IN_PROGRESS",
  test_mode: {
    active: true,
    code: "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE",
    display_required: true,
    banner_text:
      "TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED",
    session_id: "kvk-2026-08-08",
  },
};

test("classifies storage unavailability without exposing backend details", () => {
  expect(
    classifyCropDiagnosisFailure({
      status: 503,
      errorCode: "storage_provider_unavailable",
    }),
  ).toMatchObject({
    outcome: "blocked",
    status: "storage_unavailable",
  });
});

test("classifies a consumed confirmation token as an actionable replay result", () => {
  expect(
    classifyCropDiagnosisFailure({
      status: 422,
      errorCode: "CROP_CONFIRMATION_REPLAYED",
    }),
  ).toEqual({
    outcome: "blocked",
    status: "confirmation_replayed",
    crop_id: null,
    message:
      "This photo was already analyzed. Take a new photo to analyze again.",
    diagnosis: null,
  });
});

test("parses a supported prediction", () => {
  expect(parseCropDiagnosisResponse(accepted, "rice", ["rice_blast"])).toEqual(
    accepted,
  );
});

test("maps crop identity uncertainty to a visible fail-closed result", () => {
  expect(
    classifyCropDiagnosisFailure({
      response: { data: { detail: { code: "CROP_IDENTITY_UNCERTAIN" } } },
    }),
  ).toEqual({
    outcome: "blocked",
    status: "crop_identity_uncertain",
    crop_id: null,
    message: "Crop identity could not be verified. Use a clearer crop photo.",
    diagnosis: null,
  });
});

test.each([
  "invalid_image",
  "crop_not_supported",
  "runtime_not_ready",
  "field_validation_pending",
  "farmer_inference_blocked",
  "pilot_authorization_required",
  "out_of_domain",
  "model_load_failed",
  "internal_error",
] as const)("preserves backend safety response %s", (status) => {
  expect(
    parseCropDiagnosisResponse(
      { status, crop_id: "rice", message: "Safe refusal." },
      "rice",
      ["rice_blast"],
    ),
  ).toMatchObject({ outcome: "blocked", status, diagnosis: null });
});

test("rejects malformed and cross-crop responses", () => {
  expect(
    parseCropDiagnosisResponse({ ...accepted, crop_id: "cotton" }, "rice", [
      "rice_blast",
    ]),
  ).toMatchObject({ status: "malformed_response" });
  expect(parseCropDiagnosisResponse({}, "rice", ["rice_blast"])).toMatchObject({
    status: "malformed_response",
  });
});

test("rejects a legacy response whose mandatory display marker is absent or altered", () => {
  const { test_mode: _missing, ...withoutMarker } = accepted;
  expect(
    parseCropDiagnosisResponse(withoutMarker, "rice", ["rice_blast"]),
  ).toMatchObject({ status: "malformed_response" });
  expect(
    parseCropDiagnosisResponse(
      {
        ...accepted,
        test_mode: { ...accepted.test_mode, display_required: false },
      },
      "rice",
      ["rice_blast"],
    ),
  ).toMatchObject({ status: "malformed_response" });
});

test("rejects an abstention that exposes a disease class", () => {
  expect(
    parseCropDiagnosisResponse(
      { ...accepted, outcome: "uncertain", accepted: false },
      "rice",
      ["rice_blast"],
    ),
  ).toMatchObject({ status: "malformed_response" });
});

test("distinguishes timeout, offline, and server failures", () => {
  expect(classifyCropDiagnosisFailure({ code: "ETIMEDOUT" })).toMatchObject({
    status: "timeout",
  });
  expect(classifyCropDiagnosisFailure({ code: "ERR_NETWORK" })).toMatchObject({
    status: "offline",
  });
  expect(classifyCropDiagnosisFailure(new Error("500"))).toMatchObject({
    status: "server_error",
  });
});

test.each([
  ["TESTER_ROLE_REQUIRED", 403, "tester_role_required"],
  ["AUTHORIZATION_UNAVAILABLE", 403, "authorization_unavailable"],
  ["GENERAL_FARMER_INFERENCE_NOT_AUTHORIZED", 403, "release_not_authorized"],
  ["MODEL_NOT_AVAILABLE", 503, "runtime_not_ready"],
  ["RUNTIME_INTEGRITY_FAILURE", 503, "model_integrity_failure"],
  ["CROP_CONFIRMATION_EXPIRED", 422, "confirmation_expired"],
  ["CROP_CONFIRMATION_REQUIRED", 422, "confirmation_required"],
  ["CROP_CONFIRMATION_TOKEN_MISMATCH", 422, "confirmation_mismatch"],
  ["CROP_IMAGE_MISMATCH", 422, "confirmation_mismatch"],
  ["CROP_CONFIRMATION_REPLAYED", 422, "confirmation_replayed"],
  ["IMAGE_FORMAT_UNSUPPORTED", 415, "unsupported_image"],
  ["IMAGE_DECODE_FAILED", 422, "invalid_image"],
  ["LOW_QUALITY_IMAGE", 422, "low_quality_image"],
  ["OUT_OF_DOMAIN_IMAGE", 422, "out_of_domain"],
  ["AUTHENTICATION_REQUIRED", 401, "authentication_required"],
  ["anything", 429, "throttled"],
] as const)("maps backend code %s precisely", (errorCode, status, expected) => {
  expect(classifyCropDiagnosisFailure({ errorCode, status })).toMatchObject({
    status: expected,
  });
});
