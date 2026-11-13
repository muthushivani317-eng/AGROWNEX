import { mapGroundnutError, mapGroundnutInputApiError } from "../errorMapping";

test.each([
  [{ status: 401 }, "authentication"],
  [{ status: 403 }, "authorization"],
  [{ status: 413 }, "too_large"],
  [{ status: 415 }, "invalid_type"],
  [{ status: 422 }, "corrupted"],
  [{ status: 429 }, "rate_limited"],
  [
    { status: 503, errorCode: "GROUNDNUT_EXPERIMENT_DISABLED" },
    "feature_disabled",
  ],
  [{ status: 503 }, "backend_unavailable"],
  [{ status: 500 }, "server_error"],
] as const)("maps backend error %j to %s", (error, expected) => {
  expect(mapGroundnutError(error)).toBe(expected);
});

test.each([
  [401, "authentication"],
  [403, "authorization"],
  [413, "too_large"],
  [415, "unsupported_type"],
  [422, "invalid_input"],
  [503, "unavailable"],
  [500, "unknown"],
] as const)("maps symptom HTTP %s to %s", (status, expected) => {
  expect(mapGroundnutInputApiError({ status })).toBe(expected);
});
