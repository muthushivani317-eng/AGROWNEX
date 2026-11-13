import { ApiError } from "@/types";

export type GroundnutUiError =
  | "invalid_type"
  | "too_large"
  | "corrupted"
  | "authentication"
  | "authorization"
  | "rate_limited"
  | "feature_disabled"
  | "backend_unavailable"
  | "server_error";

export type GroundnutInputApiError =
  | "authentication"
  | "authorization"
  | "too_large"
  | "unsupported_type"
  | "invalid_input"
  | "unavailable"
  | "unknown";

export function mapGroundnutInputApiError(error: unknown): GroundnutInputApiError {
  const apiError = error as Partial<ApiError>;
  if (apiError.status === 401) return "authentication";
  if (apiError.status === 403) return "authorization";
  if (apiError.status === 413) return "too_large";
  if (apiError.status === 415) return "unsupported_type";
  if (apiError.status === 422) return "invalid_input";
  if (apiError.status === 503 || apiError.status === 0) return "unavailable";
  return "unknown";
}

export function mapGroundnutError(error: unknown): GroundnutUiError {
  if (error instanceof Error && error.message === "unsupported_type") {
    return "invalid_type";
  }
  if (error instanceof Error && error.message === "too_large") {
    return "too_large";
  }
  const apiError = error as Partial<ApiError>;
  if (apiError.status === 401) return "authentication";
  if (apiError.status === 403) return "authorization";
  if (apiError.status === 413) return "too_large";
  if (apiError.status === 415) return "invalid_type";
  if (apiError.status === 422) return "corrupted";
  if (apiError.status === 429) return "rate_limited";
  if (
    apiError.status === 503 &&
    apiError.errorCode === "GROUNDNUT_EXPERIMENT_DISABLED"
  ) {
    return "feature_disabled";
  }
  if (apiError.status === 0 || apiError.status === 503) {
    return "backend_unavailable";
  }
  return "server_error";
}
