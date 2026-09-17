import { actionStatusLabelKey, submitErrorMessageKey } from "../types";

it("labels completion as farmer reported rather than verified success", () => {
  expect(actionStatusLabelKey("farmer_reported_done")).toBe(
    "actionVerification.status.farmer_reported_done",
  );
  expect(actionStatusLabelKey("farmer_reported_done")).not.toContain("success");
});

describe("submitErrorMessageKey", () => {
  it("distinguishes a version conflict from a generic network error", () => {
    expect(
      submitErrorMessageKey({ status: 409, errorCode: "ACTION_VERSION_CONFLICT" }),
    ).toBe("actionVerification.versionConflict");
  });

  it("distinguishes an expired action from a generic network error", () => {
    expect(
      submitErrorMessageKey({ status: 409, errorCode: "ACTION_EXPIRED" }),
    ).toBe("actionVerification.actionExpired");
  });

  it("falls back to the network-error copy for anything else, including a real network drop", () => {
    expect(submitErrorMessageKey({ status: 0, errorCode: "" })).toBe(
      "actionVerification.networkError",
    );
    expect(submitErrorMessageKey(new Error("boom"))).toBe(
      "actionVerification.networkError",
    );
    expect(submitErrorMessageKey(null)).toBe("actionVerification.networkError");
  });
});
