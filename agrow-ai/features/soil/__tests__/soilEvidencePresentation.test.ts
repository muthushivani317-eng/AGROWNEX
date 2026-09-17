import { evidenceLabelKey } from "../services/soilEvidencePresentation";

const evidence = (evidenceType: string) =>
  ({ evidenceType }) as Parameters<typeof evidenceLabelKey>[0];

describe("soil evidence presentation", () => {
  it.each([
    ["laboratory_measured", "soil.evidenceLabMeasured"],
    ["report_extracted", "soil.evidenceReportExtracted"],
    ["user_entered", "soil.evidenceUserEntered"],
    ["remote_sensing_estimate", "soil.evidenceRemoteEstimate"],
    ["model_estimate", "soil.evidenceModelEstimate"],
  ])("labels %s without claiming all values are measured", (source, key) => {
    expect(evidenceLabelKey(evidence(source))).toBe(key);
  });

  it("keeps missing evidence unavailable", () => {
    expect(evidenceLabelKey(undefined)).toBe("soil.evidenceUnavailable");
  });
});
