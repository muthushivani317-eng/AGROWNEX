import { ApiError } from "@/types";

/** A farm without a first growth photo has no crop-cycle session yet. */
export function isMissingGrowthSession(error: unknown): boolean {
  return (
    error instanceof ApiError && error.status === 404 && error.errorCode === "growth_session_not_found"
  );
}
