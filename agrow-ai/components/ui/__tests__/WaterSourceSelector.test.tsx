import fs from "node:fs";
import path from "node:path";

const source = fs.readFileSync(
  path.resolve(__dirname, "..", "WaterSourceSelector.tsx"),
  "utf8",
);

describe("WaterSourceSelector presentation contract", () => {
  it("keeps each bilingual option in one horizontal full-width row", () => {
    expect(source).toMatch(
      /option:\s*\{[\s\S]*width:\s*["']100%["'][\s\S]*flexDirection:\s*["']row["']/,
    );
    expect(source).toContain("styles.optionIcon");
    expect(source).toContain("styles.optionCopy");
  });

  it("pins the selection control to the right side", () => {
    expect(source).toMatch(
      /radio:\s*\{[\s\S]*flexShrink:\s*0[\s\S]*marginLeft:\s*["']auto["']/,
    );
    expect(source).toContain("styles.selectedRadio");
  });

  it("preserves accessible radio selection behavior", () => {
    expect(source).toContain('accessibilityRole="radio"');
    expect(source).toContain("accessibilityState={{ selected }}");
    expect(source).toContain("onSelect(item.value)");
  });
});
