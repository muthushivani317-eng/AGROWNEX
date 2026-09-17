import {
  formatDiagnosisName,
  friendlyDiagnosisError,
} from "../screens/GeneralDiagnosisScreen";

/**
 * GeneralDiagnosisScreen previously rendered a caught error's raw `.message`
 * straight to the farmer on failure (untranslated, sometimes a technical
 * string from the network layer) instead of friendly copy (2026-08
 * pre-release audit). These lock in that it never does that again.
 */
describe("friendlyDiagnosisError", () => {
  const translate = (key: string, opts?: { defaultValue?: string }) =>
    opts?.defaultValue ?? key;

  it.each(["IMAGE_UNUSABLE", "IMAGE_TOO_SMALL", "INSUFFICIENT_DETAIL", "validation_error"])("does not call a rejected photo a service outage: %s", (errorCode) => {
    expect(friendlyDiagnosisError({ status: 422, errorCode }, translate)).toContain("Check the selected crop");
  });

  it.each([["EXTREME_DARKNESS", "too dark"], ["EXTREME_BRIGHTNESS", "too bright"], ["IMAGE_SIZE_INVALID", "too large"], ["IMAGE_FORMAT_UNSUPPORTED", "JPEG or PNG"]])("explains %s", (errorCode, expected) => {
    expect(friendlyDiagnosisError({ status: 422, errorCode }, translate)).toContain(expected);
  });

  it("never surfaces the raw error message, even a technical one", () => {
    const raw = new Error(
      "AxiosError: Request failed with status code 500 at /disease/predict",
    );
    const result = friendlyDiagnosisError(raw, translate);
    expect(result).not.toContain("AxiosError");
    expect(result).not.toContain("status code");
  });

  it("shows offline copy for a network error", () => {
    const networkError = { isNetwork: true, message: "Network Error" };
    expect(friendlyDiagnosisError(networkError, translate)).toBe(
      "Check your internet connection and try again.",
    );
  });

  it("shows a timing-out message for a slow diagnosis, not a network error (2026-09-03 regression)", () => {
    // A client-side timeout and a genuine offline device both surface as
    // ApiError.isNetwork (status 0) in this codebase, but only a timeout
    // also sets isTimeout — the diagnosis screen must prefer that signal so
    // a slow-but-working request is never reported as "no network".
    const timeoutError = {
      isNetwork: true,
      isTimeout: true,
      message: "timeout of 45000ms exceeded",
    };
    expect(friendlyDiagnosisError(timeoutError, translate)).toBe(
      "The photo is taking longer than usual to analyze. Please try again in a moment.",
    );
  });

  it("shows the generic diagnosis-failed copy for a non-network error", () => {
    const serverError = {
      isNetwork: false,
      status: 500,
      message: "Internal Server Error",
    };
    expect(friendlyDiagnosisError(serverError, translate)).toBe(
      "The diagnosis service is temporarily unavailable. Please try again.",
    );
  });

  it("handles a plain thrown value gracefully", () => {
    expect(friendlyDiagnosisError("boom", translate)).toBe(
      "The diagnosis service is temporarily unavailable. Please try again.",
    );
    expect(friendlyDiagnosisError(null, translate)).toBe(
      "The diagnosis service is temporarily unavailable. Please try again.",
    );
  });
});

describe("formatDiagnosisName", () => {
  it("turns a model class identifier into a readable diagnosis", () => {
    expect(formatDiagnosisName("banana__sigatoka_leaf_spot")).toBe(
      "Sigatoka Leaf Spot",
    );
  });

  it("preserves an absent diagnosis", () => {
    expect(formatDiagnosisName(null)).toBeNull();
  });
});
