import {
  guidedDecisionCopyKey,
  validateGuidedEvidence,
} from "../guidedDiagnosis";

describe("guided multi-photo diagnosis safety", () => {
  test("allows one primary photo plus three unique guided views", () => {
    expect(
      validateGuidedEvidence([
        "affected_leaf",
        "whole_plant",
        "lesion_closeup",
        "leaf_underside",
      ]),
    ).toBeNull();
  });

  test("fails closed for duplicate or excessive views", () => {
    expect(validateGuidedEvidence(["affected_leaf", "affected_leaf"])).toBe(
      "duplicate_view",
    );
    expect(
      validateGuidedEvidence([
        "affected_leaf",
        "whole_plant",
        "lesion_closeup",
        "leaf_underside",
        "whole_plant",
      ]),
    ).toBe("too_many_images");
  });

  test("conflict and unknown outcomes never map to a likely diagnosis", () => {
    expect(guidedDecisionCopyKey("conflict_needs_more_evidence")).toBe(
      "disease.guided.conflict",
    );
    expect(guidedDecisionCopyKey("unsupported_or_unknown_disease")).toBe(
      "disease.guided.unknown",
    );
  });
});
