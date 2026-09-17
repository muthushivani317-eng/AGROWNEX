import { DISEASE_DETECTION_CROP_IDS, DISEASE_DETECTION_CROPS } from "../crops";

describe("Disease Detection crop catalogue", () => {
  it("provides a complete label for every supported disease crop", () => {
    expect(DISEASE_DETECTION_CROPS.map((crop) => crop.id)).toEqual([
      ...DISEASE_DETECTION_CROP_IDS,
    ]);
    expect(DISEASE_DETECTION_CROPS).toHaveLength(11);
    for (const crop of DISEASE_DETECTION_CROPS) {
      expect(crop.en).toBeTruthy();
      expect(crop.ta).toBeTruthy();
    }
  });
});
