import { ApiError } from "@/types";

import { diseaseRiskErrorMessageKey } from "../errors";

const apiError = (status: number, errorCode: string) =>
  new ApiError({ status, errorCode, message: "server detail must not be shown" });

describe("diseaseRiskErrorMessageKey", () => {
  it.each([
    [apiError(0, "network_error"), "diseaseRisk.errors.network"],
    [apiError(401, "AUTHENTICATION_REQUIRED"), "diseaseRisk.errors.authentication"],
    [apiError(403, "AUTHENTICATION_INVALID"), "diseaseRisk.errors.authentication"],
    [apiError(404, "FARM_NOT_OWNED"), "diseaseRisk.errors.farmAccess"],
    [apiError(422, "VALIDATION_ERROR"), "diseaseRisk.errors.validation"],
    [apiError(503, "RULE_REGISTRY_UNAVAILABLE"), "diseaseRisk.errors.unavailable"],
    [apiError(500, "http_error"), "diseaseRisk.errors.server"],
    [new Error("unknown"), "diseaseRisk.errors.server"],
  ])("maps %p to %s", (error, key) => {
    expect(diseaseRiskErrorMessageKey(error)).toBe(key);
  });

  it("does not classify the saved no-rule result as an error", () => {
    expect(
      diseaseRiskErrorMessageKey(
        apiError(200, "NO_VERIFIED_RULE_AVAILABLE"),
      ),
    ).toBe("diseaseRisk.errors.server");
  });
});
