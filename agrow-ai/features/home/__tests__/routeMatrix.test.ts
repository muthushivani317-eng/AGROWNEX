import { HOME_FEATURE_ROUTES } from "../routes";

describe("authenticated Home feature route matrix", () => {
  it("maps every visible feature to its actual non-placeholder pathname", () => {
    expect(HOME_FEATURE_ROUTES).toEqual({
      ai: "/ai",
      disease: "/disease",
      diseaseRisk: "/disease-risk",
      weather: "/weather",
      satellite: "/satellite",
      addFarm: "/farm/new",
      calendar: "/calendar",
      growth: "/growth",
      harvestReadiness: "/harvest-readiness",
      actionVerification: "/action-verification",
      market: "/market",
      experts: "/consultations",
      schemes: "/schemes",
      sell: "/produce",
      notifications: "/notifications",
      plantIdentifier: "/plant-identifier",
      soil: "/soil",
      nutrient: "/nutrient",
      lcc: "/lcc",
      inputs: "/inputs",
      intelligence: "/intelligence",
      memory: "/memory",
      cropRecommendation: "/crop-recommendation",
      equipment: "/equipment",
      community: "/community",
      knowledge: "/knowledge",
      organic: "/organic",
    });
    expect(Object.values(HOME_FEATURE_ROUTES)).not.toContain("/");
  });
});
