import { getIndicatorAvailabilityLabel } from "../utils/getIndicatorAvailabilityLabel";
import { en } from "../../../localization/locales/en";
import { ta } from "../../../localization/locales/ta";

describe("getIndicatorAvailabilityLabel", () => {
  it.each([
    "salinity_risk",
    "organic_matter_trend",
    "acidity_ph_risk",
  ])("marks unavailable %s as requiring a lab report", (code) => {
    expect(getIndicatorAvailabilityLabel(code, "insufficient")).toBe(
      "lab_report_required",
    );
  });

  it("keeps mapped organic carbon as ordinary insufficient data", () => {
    expect(
      getIndicatorAvailabilityLabel("organic_carbon_estimate", "insufficient"),
    ).toBe("insufficient");
  });

  it("keeps satellite indicators as ordinary insufficient data", () => {
    expect(getIndicatorAvailabilityLabel("soil_moisture", "insufficient")).toBe(
      "insufficient",
    );
  });

  it("always labels an available result as available", () => {
    expect(getIndicatorAvailabilityLabel("salinity_risk", "available")).toBe(
      "available",
    );
  });

  it("provides a localized, explicit label for laboratory-only results", () => {
    expect(en.soil.labReportRequired).toBe("Lab result required");
    expect(ta.soil.labReportRequired).toBe(
      "ஆய்வகப் பரிசோதனை முடிவு தேவை",
    );
  });
});
