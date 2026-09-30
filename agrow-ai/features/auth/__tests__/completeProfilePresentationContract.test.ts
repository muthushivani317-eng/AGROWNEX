import fs from "node:fs";
import path from "node:path";

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, "../../..", relative), "utf8");

describe("bilingual complete-profile presentation contract", () => {
  const screen = read("features/auth/screens/CompleteProfileScreen.tsx");
  const productPicker = read("features/auth/components/ProductMultiSelect.tsx");
  const onboardingData = read("features/auth/components/onboardingData.ts");
  const catalogHook = read("features/auth/hooks/useFarmCatalog.ts");
  const english = read("localization/locales/en.ts");
  const tamil = read("localization/locales/ta.ts");

  it("preserves the working submission, GPS and dependent location behavior", () => {
    expect(screen).toContain("complete.mutate(data");
    expect(screen).toContain("autofillAddressFromGPS()");
    expect(screen).toMatch(
      /setValue\(["']block["'], ["']["'](, \{ shouldDirty: true \})?\)/,
    );
    expect(screen).toMatch(
      /setValue\(["']village["'], ["']["'](, \{ shouldDirty: true \})?\)/,
    );
  });

  it("uses accessible large controls without emoji crop icons", () => {
    expect(productPicker).toContain('accessibilityRole="checkbox"');
    expect(productPicker).toContain("accessibilityState={{ checked: selected }}");
    expect(screen).toContain("minHeight: 44");
    expect(screen).toContain("minHeight: 58");
    expect(screen).toContain("ProductMultiSelect");
    expect(screen).toContain("farmProducts");
    expect(screen).toContain("expectedHarvestMonth");
    expect(screen).toContain("availableForSale");
    expect(screen).not.toMatch(/[🍌🌾☁️🥜🌶️🫘]/u);
  });

  it("loads the product and category choices from the backend catalog", () => {
    expect(catalogHook).toContain("endpoints.farmers.farmCatalog");
    expect(screen).toContain("catalog.data.items");
    expect(productPicker).toContain("products.filter");
    expect(onboardingData).not.toContain("ONBOARDING_PRODUCTS");
    expect(onboardingData).not.toContain("Paddy");
  });

  it("shows consent before directory choices and sends real join requests", () => {
    expect(screen.indexOf("copy.both")).toBeLessThan(screen.indexOf('<OrganizationDirectory kind="fpo"'));
    expect(screen).toContain("usePartnerDirectory(kind, district");
    expect(screen).toContain("join.mutate(organizationId");
  });

  it("ships matching English and Tamil profile copy and language switching", () => {
    expect(screen).toContain("void setLanguage(nextLanguage)");
    expect(english).toContain('setupEyebrow: "PROFILE SETUP"');
    expect(english).toContain('aboutYou: "About you"');
    expect(tamil).toContain('setupEyebrow: "சுயவிவர அமைப்பு"');
    expect(tamil).toContain('aboutYou: "உங்களைப் பற்றி"');
  });

  it("implements the required five-step farmer journey", () => {
    expect(screen).toContain("விவசாயி விவரங்கள்");
    expect(screen).toContain("பண்ணை இருப்பிடம்");
    expect(screen).toContain("பயிர்கள் & விளைபொருட்கள்");
    expect(screen).toContain("FPO / KVK");
    expect(screen).toContain("சரிபார்த்து சமர்ப்பிக்கவும்");
  });
});
