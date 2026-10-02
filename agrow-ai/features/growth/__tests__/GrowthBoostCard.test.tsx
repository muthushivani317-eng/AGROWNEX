const React = require("react");
const TestRenderer = require("react-test-renderer");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${JSON.stringify(options)}` : key,
  }),
}));
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});
jest.mock("@/components/ui", () => {
  const { Text } = require("react-native");
  return { AgText: Text };
});

import { GrowthBoostCard } from "../components/GrowthBoostCard";
import type { GrowthAnalysis, GrowthScheduleStatus } from "../types";

const analysis: GrowthAnalysis = {
  growthStage: "vegetative",
  plantVigor: "good",
  healthScore: 70,
  confidence: 80,
  leafColorObservations: [],
  visibleAbnormalities: [],
  changesFromPrevious: [],
  recommendations: ["AI tip"],
  diseaseResult: null,
  nutrientResult: null,
  needsExpertReview: false,
  growthSummaryTamil: null,
  growthSummaryEnglish: null,
  modelUsed: null,
};

function render(props: Record<string, unknown>) {
  let tree: any;
  TestRenderer.act(() => {
    tree = TestRenderer.create(React.createElement(GrowthBoostCard, props));
  });
  return JSON.stringify(tree.toJSON());
}

const behind: GrowthScheduleStatus = {
  behind: true,
  reasons: ["overdue_task", "stage_lagging"],
  overdueTasks: 2,
  expectedStage: "flowering",
  observedStage: "vegetative",
};

describe("GrowthBoostCard", () => {
  it("on schedule: AI tips, then organic, then chemical", () => {
    const out = render({ analysis });
    expect(out).not.toContain("growth.boost.behindTitle");
    expect(out.indexOf("AI tip")).toBeLessThan(out.indexOf("growth.boost.vegetative.organic"));
    expect(out.indexOf("growth.boost.vegetative.organic")).toBeLessThan(
      out.indexOf("growth.boost.vegetative.chemical"),
    );
  });

  it("behind schedule: warning, then organic boost leads before AI tips and chemical", () => {
    const out = render({ analysis, scheduleStatus: behind });
    const warning = out.indexOf("growth.boost.behindTitle");
    const organic = out.indexOf("growth.boost.vegetative.organic");
    expect(warning).toBeGreaterThan(-1);
    expect(out).toContain("growth.boost.behindOverdue");
    expect(out).toContain("growth.boost.behindStage");
    expect(warning).toBeLessThan(organic);
    expect(organic).toBeLessThan(out.indexOf("AI tip"));
    expect(organic).toBeLessThan(out.indexOf("growth.boost.vegetative.chemical"));
  });

  it("behind with no photo yet uses the observed/expected stage and hides chemicals in conversion", () => {
    const out = render({ analysis: null, scheduleStatus: behind, chemicalPolicy: "hide" });
    expect(out).toContain("growth.boost.vegetative.organic");
    expect(out).not.toContain("growth.boost.vegetative.chemical");
    expect(out).toContain("organic.chemicalNotAllowed");
  });

  it("renders nothing with no photo and not behind", () => {
    expect(render({ analysis: null, scheduleStatus: { ...behind, behind: false, reasons: [] } })).toBe("null");
  });
});
