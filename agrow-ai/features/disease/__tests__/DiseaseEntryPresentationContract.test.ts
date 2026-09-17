import fs from "node:fs";
import path from "node:path";

const screen = fs.readFileSync(
  path.resolve(__dirname, "../screens/DiseaseScreen.tsx"),
  "utf8",
);
const generalScreen = fs.readFileSync(
  path.resolve(__dirname, "../screens/GeneralDiagnosisScreen.tsx"),
  "utf8",
);

describe("Disease Detection entry presentation contract", () => {
  it("keeps the approved field-guide structure and localized copy", () => {
    expect(screen).toContain("backgroundColor={ENTRY_BG}");
    expect(screen).toContain('t("disease.plantHealth")');
    expect(screen).toContain('t("disease.goodLight")');
    expect(screen).toContain('t("disease.closeView")');
    expect(screen).toContain('t("disease.oneLeaf")');
    expect(screen).toContain('t("disease.youStayInControl")');
    expect(screen).toContain('t("disease.entryDisclaimer")');
  });

  it("preserves capture, gallery, history, and crop safety behavior", () => {
    expect(screen).toContain('identifyPhotoCrop("camera")');
    expect(screen).toContain('identifyPhotoCrop("gallery")');
    expect(screen).toContain('router.push("/disease/history")');
    expect(screen).toContain('t("disease.cropIdentificationCaution")');
    expect(screen).toContain("accessibilityState={{");
  });

  it("uses accessible touch-sized controls and the approved light palette", () => {
    expect(screen).toContain('const ENTRY_BG = "#F8F5EC"');
    expect(screen).toContain("minHeight: 56");
    expect(screen).toContain("width: 48, height: 48");
    expect(screen).not.toContain("transform: [{ scale:");
    expect(screen).toContain('backgroundColor: "#F2B632"');
    expect(screen).toContain("primaryActionText: { color: ENTRY_TEXT }");
  });

  it("shows the approved design to regular farmers routed through general diagnosis", () => {
    expect(screen).toContain("return <GeneralDiagnosisScreen />");
    expect(generalScreen).toContain("backgroundColor={ENTRY.background}");
    expect(generalScreen).toMatch(/t\(["']disease\.goodLight["']\)/);
    expect(generalScreen).toMatch(/t\(["']disease\.closeView["']\)/);
    expect(generalScreen).toMatch(/t\(["']disease\.oneLeaf["']\)/);
    expect(generalScreen).toMatch(/takePhoto\(["']camera["']\)/);
    expect(generalScreen).toMatch(/takePhoto\(["']gallery["']\)/);
    expect(generalScreen).toContain('testID="general-crop-grid"');
    expect(generalScreen).toContain("testID={`general-crop-${item}`}");
    expect(generalScreen).toContain('flexDirection: "column"');
    expect(generalScreen).toContain("width: 48");
    expect(generalScreen).toContain("accessibilityElementsHidden");
    expect(generalScreen).toContain('backgroundColor: "#F2B632"');
    expect(generalScreen).toContain("cameraButtonText: { color: ENTRY.text }");
    expect(generalScreen).toContain("DISEASE_DETECTION_CROP_IDS.map");
    expect(generalScreen).not.toContain('<Camera size={24} color="#FFFFFF" />');
    expect(generalScreen).toContain("backgroundColor={ENTRY.background}");
  });
});
