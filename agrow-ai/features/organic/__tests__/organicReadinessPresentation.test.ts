import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "../../..");
const screen = fs.readFileSync(
  path.join(root, "features/organic/screens/OrganicReadinessScreen.tsx"),
  "utf8",
);

describe("organic readiness presentation contract", () => {
  it("renders the illustrated header, completion progress, question cards, and result action", () => {
    expect(screen).toContain("organic-dashboard-landscape.png");
    expect(screen).toContain("<ProgressSummary");
    expect(screen).toContain("<QuestionCard");
    expect(screen).toContain('t("organic.readinessSubmit")');
  });

  it("keeps the assessment server-driven and preserves every async state", () => {
    expect(screen).toContain("useOrganicReadinessQuestions()");
    expect(screen).toContain("useSubmitOrganicReadiness(farmId)");
    expect(screen).toContain("questionsQuery.isLoading");
    expect(screen).toContain("questionsQuery.isError");
    expect(screen).toContain("questions.length === 0");
    expect(screen).toContain("submit.isError");
  });

  it("uses accessible native selection and submission controls", () => {
    expect(screen).toContain('accessibilityRole="radiogroup"');
    expect(screen).toContain('accessibilityRole="radio"');
    expect(screen).toContain('accessibilityRole="progressbar"');
    expect(screen).toContain('accessibilityRole="button"');
  });
});
