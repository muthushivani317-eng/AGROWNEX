import type {
  CropDiagnosisResult,
  CropPredictionResult,
  CropSafetyStatus,
} from "./types";

const SAFETY_STATUSES = new Set<CropSafetyStatus>([
  "invalid_image",
  "crop_not_supported",
  "runtime_not_ready",
  "field_validation_pending",
  "farmer_inference_blocked",
  "pilot_authorization_required",
  "out_of_domain",
  "crop_identity_uncertain",
  "model_load_failed",
  "internal_error",
]);
const LEGACY_TEST_MODE_MARKER =
  "TEST MODE \u2014 NOT AUTHORIZED FOR GENERAL RELEASE \u2014 RESULT NOT VALIDATED";
const RESTRICTED_TEST_MODE_CODE = "RESTRICTED_CROP_CONTROLLED_TEST";

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function parseCropDiagnosisResponse(
  value: unknown,
  expectedCropId: string,
  supportedClassIds: readonly string[],
): CropDiagnosisResult {
  const body = record(value);
  if (!body) return malformed();

  const safetyStatus =
    typeof body.status === "string"
      ? (body.status.toLocaleLowerCase("en-US") as CropSafetyStatus)
      : null;
  if (safetyStatus && SAFETY_STATUSES.has(safetyStatus)) {
    const cropId = typeof body.crop_id === "string" ? body.crop_id : null;
    if (cropId !== null && cropId !== expectedCropId)
      return malformed("Crop response mismatch.");
    return {
      outcome: "blocked",
      status: safetyStatus,
      crop_id: cropId,
      message:
        typeof body.message === "string"
          ? body.message
          : "The image could not be safely assessed.",
      diagnosis: null,
    };
  }

  const outcome = body.outcome;
  const cropId = body.crop_id;
  const classId = body.class_id;
  const testMode = record(body.test_mode);
  if (
    (outcome !== "accepted" && outcome !== "uncertain") ||
    cropId !== expectedCropId ||
    body.crop_identity_source !== "user_confirmed_not_ai_verified" ||
    (classId !== null && typeof classId !== "string") ||
    !["low", "moderate", "high"].includes(
      String(body.qualitative_confidence),
    ) ||
    typeof body.calibrated_confidence !== "number" ||
    !Number.isFinite(body.calibrated_confidence) ||
    body.calibrated_confidence < 0 ||
    body.calibrated_confidence > 1 ||
    typeof body.accepted !== "boolean" ||
    body.official_accuracy_claim !== false ||
    typeof body.field_validation_status !== "string" ||
    testMode?.active !== true ||
    testMode.code !== "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE" ||
    testMode.display_required !== true ||
    testMode.banner_text !== LEGACY_TEST_MODE_MARKER ||
    typeof testMode.session_id !== "string" ||
    testMode.session_id.length === 0
  )
    return malformed();

  if (
    outcome === "uncertain" &&
    (classId !== null || body.accepted !== false)
  ) {
    return malformed("Unsafe abstention response.");
  }
  if (
    outcome === "accepted" &&
    (typeof classId !== "string" ||
      !supportedClassIds.includes(classId) ||
      body.accepted !== true)
  )
    return malformed("Unsupported class response.");

  return body as unknown as CropPredictionResult;
}

export function parseRestrictedCropDiagnosisResponse(
  value: unknown,
  expectedCropId: string,
  supportedClassIds: readonly string[],
): CropDiagnosisResult {
  const body = record(value);
  const testMode = record(body?.test_mode);
  if (
    !body ||
    body.crop_id !== expectedCropId ||
    body.restricted_runtime !== true ||
    body.field_validated !== false ||
    body.recommendation_available !== false ||
    body.official_accuracy_claim !== false ||
    testMode?.active !== true ||
    testMode.code !== RESTRICTED_TEST_MODE_CODE ||
    testMode.display_required !== true ||
    testMode.banner_text !== LEGACY_TEST_MODE_MARKER
  )
    return malformed();

  if (body.status === "runtime_error") {
    return {
      outcome: "blocked",
      status: "model_load_failed",
      crop_id: expectedCropId,
      message: "The restricted diagnosis runtime is unavailable.",
      diagnosis: null,
    };
  }
  if (
    typeof body.confidence !== "number" ||
    !Number.isFinite(body.confidence) ||
    body.confidence < 0 ||
    body.confidence > 1 ||
    typeof body.margin !== "number" ||
    !Number.isFinite(body.margin) ||
    body.margin < 0 ||
    body.margin > 1
  )
    return malformed();
  if (body.status === "abstained") {
    return {
      outcome: "uncertain",
      crop_id: expectedCropId,
      crop_identity_source: "user_confirmed_not_ai_verified",
      class_id: null,
      qualitative_confidence: "low",
      calibrated_confidence: body.confidence,
      margin: body.margin,
      accepted: false,
      official_accuracy_claim: false,
      field_validation_status: "IN_PROGRESS",
      test_mode: testMode as unknown as CropPredictionResult["test_mode"],
    };
  }
  if (
    body.status !== "accepted" ||
    typeof body.predicted_label !== "string" ||
    !supportedClassIds.includes(body.predicted_label)
  )
    return malformed("Unsupported restricted-runtime result.");
  return {
    outcome: "accepted",
    crop_id: expectedCropId,
    crop_identity_source: "user_confirmed_not_ai_verified",
    class_id: body.predicted_label,
    qualitative_confidence: "high",
    calibrated_confidence: body.confidence,
    margin: body.margin,
    accepted: true,
    official_accuracy_claim: false,
    field_validation_status: "IN_PROGRESS",
    test_mode: testMode as unknown as CropPredictionResult["test_mode"],
    report_id: typeof body.report_id === "string" ? body.report_id : null,
    review_status:
      body.review_status === "pending" || body.review_status === "declined"
        ? body.review_status
        : null,
    kvk_session: body.kvk_session === true,
  };
}

export function classifyCropDiagnosisFailure(
  error: unknown,
): CropDiagnosisResult {
  const candidate = record(error);
  const code = typeof candidate?.code === "string" ? candidate.code : "";
  const errorCode =
    typeof candidate?.errorCode === "string" ? candidate.errorCode : "";
  const status = typeof candidate?.status === "number" ? candidate.status : 0;
  const hasExplicitStatus = typeof candidate?.status === "number";
  const normalizedCode = (errorCode || code).toUpperCase();
  const mapped = failureStatus(normalizedCode, status, hasExplicitStatus);
  if (mapped) return blocked(mapped, failureMessage(mapped));
  if (status === 422 && errorCode === "CROP_CONFIRMATION_REPLAYED") {
    return {
      outcome: "blocked",
      status: "confirmation_replayed",
      crop_id: null,
      message:
        "This photo was already analyzed. Take a new photo to analyze again.",
      diagnosis: null,
    };
  }
  const response = record(candidate?.response);
  const data = record(response?.data);
  const detail = record(data?.detail);
  if (detail?.code === "CROP_IDENTITY_UNCERTAIN") {
    return {
      outcome: "blocked",
      status: "crop_identity_uncertain",
      crop_id: null,
      message: "Crop identity could not be verified. Use a clearer crop photo.",
      diagnosis: null,
    };
  }
  if (code === "ECONNABORTED" || code === "ETIMEDOUT")
    return transport("timeout");
  if (code === "ERR_NETWORK") return transport("offline");
  return transport("server_error");
}

function failureStatus(
  code: string,
  status: number,
  hasExplicitStatus: boolean,
): CropSafetyStatus | null {
  if (code === "STORAGE_PROVIDER_UNAVAILABLE" || code === "STORAGE_FAILED")
    return "storage_unavailable";
  if (
    code === "TESTER_ROLE_REQUIRED" ||
    code === "CONTROLLED_TESTER_ROLE_REQUIRED"
  )
    return "tester_role_required";
  if (code === "AUTHORIZATION_UNAVAILABLE") return "authorization_unavailable";
  if (
    code.includes("INFERENCE_NOT_AUTHORIZED") ||
    code === "MODEL_RELEASE_NOT_AUTHORIZED"
  )
    return "release_not_authorized";
  if (code === "AUTHENTICATION_REQUIRED" || status === 401)
    return "authentication_required";
  if (code === "CROP_CONFIRMATION_EXPIRED") return "confirmation_expired";
  if (code === "CROP_CONFIRMATION_REQUIRED") return "confirmation_required";
  if (
    code === "CROP_CONFIRMATION_TOKEN_MISMATCH" ||
    code === "CROP_IMAGE_MISMATCH"
  )
    return "confirmation_mismatch";
  if (
    code === "CROP_CONFIRMATION_REPLAYED" ||
    code === "CROP_CONFIRMATION_ALREADY_USED"
  )
    return "confirmation_replayed";
  if (
    code.includes("INTEGRITY") ||
    code === "MODEL_INTEGRITY_OR_RUNTIME_FAILURE"
  )
    return "model_integrity_failure";
  if (code === "MODEL_NOT_AVAILABLE" || code.includes("RUNTIME_NOT_READY"))
    return "runtime_not_ready";
  if (
    code.includes("FORMAT_UNSUPPORTED") ||
    code === "INVALID_IMAGE_FORMAT" ||
    code.includes("SIZE_INVALID") ||
    code.includes("TOO_LARGE")
  )
    return "unsupported_image";
  if (
    code.includes("LOW_QUALITY") ||
    code.includes("TOO_SMALL") ||
    code.includes("TOO_DARK") ||
    code.includes("OVEREXPOSED") ||
    code.includes("TOO_BLURRY")
  )
    return "low_quality_image";
  if (code.includes("OUT_OF_DOMAIN")) return "out_of_domain";
  if (
    code.includes("CORRUPT") ||
    code.includes("DECODE") ||
    code.includes("UNREADABLE") ||
    code === "INVALID_IMAGE"
  )
    return "invalid_image";
  if (status === 429) return "throttled";
  if (status === 0 && hasExplicitStatus) return "offline";
  return null;
}

function failureMessage(status: CropSafetyStatus): string {
  const messages: Partial<Record<CropSafetyStatus, string>> = {
    tester_role_required: "Controlled tester access is required.",
    authorization_unavailable: "Testing authorization could not be verified.",
    release_not_authorized: "This model is not authorized for this release.",
    authentication_required: "Sign in again before analysis.",
    confirmation_expired: "The crop confirmation expired. Take a new photo.",
    confirmation_required: "Confirm the crop for a new photo before analysis.",
    confirmation_mismatch:
      "The photo no longer matches its crop confirmation. Take a new photo.",
    confirmation_replayed:
      "This photo was already analyzed. Take a new photo to analyze again.",
    model_integrity_failure: "The model failed its integrity check.",
    storage_unavailable:
      "Secure image storage is unavailable. Please try again later.",
    runtime_not_ready: "The diagnosis runtime is unavailable.",
    unsupported_image: "This image format is not supported.",
    low_quality_image: "The image quality is too low for safe analysis.",
    out_of_domain: "The image is outside the supported crop domain.",
    invalid_image: "The image could not be decoded safely.",
    throttled: "Your limit has been reached. Try again later.",
  };
  return (
    messages[status] ?? "The diagnosis service is temporarily unavailable."
  );
}

function blocked(
  status: CropSafetyStatus,
  message: string,
): CropDiagnosisResult {
  return {
    outcome: "blocked",
    status,
    crop_id: null,
    message,
    diagnosis: null,
  };
}

function malformed(
  message = "The server returned an invalid diagnosis response.",
): CropDiagnosisResult {
  return {
    outcome: "blocked",
    status: "malformed_response",
    crop_id: null,
    message,
    diagnosis: null,
  };
}

function transport(
  status: "timeout" | "offline" | "server_error",
): CropDiagnosisResult {
  return {
    outcome: "blocked",
    status,
    crop_id: null,
    message:
      status === "timeout"
        ? "The diagnosis request timed out."
        : status === "offline"
          ? "The device appears to be offline."
          : "The diagnosis service is temporarily unavailable.",
    diagnosis: null,
  };
}
