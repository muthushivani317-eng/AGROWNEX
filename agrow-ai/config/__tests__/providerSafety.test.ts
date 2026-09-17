import { mayUseLocalFeatureMocks } from "../providerSafety";

describe("production feature provider safety", () => {
  it.each(["production", "internal_testing", "kvk_field_test"] as const)(
    "%s fails closed without a backend",
    (profile) => {
      expect(mayUseLocalFeatureMocks(profile, false)).toBe(false);
    },
  );

  it("allows local mocks only in explicit development profiles", () => {
    expect(mayUseLocalFeatureMocks("development", false)).toBe(true);
    expect(mayUseLocalFeatureMocks("localStandalone", false)).toBe(true);
    expect(mayUseLocalFeatureMocks("pilot", false)).toBe(false);
  });
});
