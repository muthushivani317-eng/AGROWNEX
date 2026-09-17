import { formatSamplingReason } from "../utils/formatSamplingReason";

describe("formatSamplingReason", () => {
  it.each([
    [
      "spatial_variability:higher_vigor_or_moisture",
      "Higher vigor or moisture",
    ],
    ["spatial_variability:lower_vigor_or_moisture", "Lower vigor or moisture"],
    ["spatial_variability_zone", "Spatial variability zone"],
  ])("formats %s as readable copy", (reason, expected) => {
    expect(formatSamplingReason(reason)).toBe(expected);
  });

  it("uses safe copy for an empty reason", () => {
    expect(formatSamplingReason("")).toBe("Sampling priority area");
  });
});
