import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const list = fs.readFileSync(
  path.join(root, "features/produce/screens/ProduceListScreen.tsx"),
  "utf8",
);
const tabs = fs.readFileSync(
  path.join(root, "features/produce/components/ProduceViewTabs.tsx"),
  "utf8",
);
const form = fs.readFileSync(
  path.join(root, "features/produce/components/ProduceForm.tsx"),
  "utf8",
);
const detail = fs.readFileSync(
  path.join(root, "features/produce/screens/ProduceDetailScreen.tsx"),
  "utf8",
);

describe("Sell Agricultural Produce presentation contract", () => {
  it("keeps tabs and both create actions visible on the fixed light surface", () => {
    expect(tabs).toContain("active === view && styles.activeTab");
    expect(tabs).toContain("activeText: { color: C.paper }");
    expect(list).toContain("backgroundColor: C.green");
    expect(list).toContain('testID="produce-add-listing-button"');
    expect(list).toContain("left: 20");
    expect(list).toContain("zIndex: 20");
    expect(list).toContain("style={styles.addButton}");
    expect(tabs).toContain("style={[");
    expect(list).toContain("emptyActionLabel={t(\"produce.create\")}");
    expect(list).toContain('router.push("/produce/new")');
    expect(list).toContain("refreshLock.current");
    expect(list).toContain("active.isLoading || active.isError ? []");
    expect(list).toContain('t("produce.cachedNotice")');
    expect(list).not.toContain("<AgOfflineBanner");
    expect(tabs).toContain("contentContainerStyle={styles.content}");
  });

  it("collects the complete procurement listing and initializes an asynchronously loaded farm", () => {
    for (const field of [
      "category",
      "productName",
      "customProductName",
      "cultivatedAreaAcres",
      "expectedTotalQuantity",
      "availableQuantity",
      "qualityNotes",
      "expectedHarvestDate",
      "availableFrom",
      "availableUntil",
      "askingPrice",
      "priceUnit",
      "packaging",
      "pickupLocation",
      "negotiable",
    ]) {
      expect(form).toContain(`name=\"${field}\"`);
    }
    expect(form).toContain("showPhotos ?");
    expect(form).toContain("if (!getValues('farmId'))");
    expect(form).toContain("setValue('farmId', firstFarm.id");
    expect(form).toContain("setValue('availabilityType', type");
    expect(form).toContain("accessibilityRole=\"radio\"");
    expect(form).toContain("maxWidth: 768");
    expect(form).toContain("<BaseAgInput {...props} light />");
    expect(form).toContain("<BaseAgDropdown {...props} light />");
    expect(form).toContain("styles.segmentSelected");
    expect(form).toContain("<TouchableOpacity");
    expect(form).toContain("size=\"lg\"");
    expect(form).toContain("data.category === 'other_produce' ? 'draft'");
  });

  it("does not render precise coordinates or contact PII in farmer listing details", () => {
    expect(detail).not.toContain('offer.latitude');
    expect(detail).not.toContain('offer.longitude');
    expect(detail).not.toContain('offer.phone');
    expect(detail).not.toContain('offer.email');
  });
});
