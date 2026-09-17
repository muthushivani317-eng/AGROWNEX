let mockUserId = "user-a";
jest.mock("@/features/auth/store/authStore", () => ({
  useAuthStore: {
    getState: () => ({ user: { id: mockUserId } }),
  },
}));

import type { DiseaseReport } from "../types";
import { localDiseaseProvider } from "../services/localDiseaseProvider";
import { diseaseStorage } from "../services/diseaseStorage";
import { appStorage } from "@/lib/storage";

let nextId = 0;

function report(overrides: Partial<DiseaseReport> = {}): DiseaseReport {
  nextId += 1;
  return {
    id: `report-${nextId}`,
    farmId: null,
    crop: "paddy",
    cropConfidence: 90,
    disease: "Leaf spot",
    confidence: 80,
    severity: "moderate",
    symptoms: ["spots"],
    causes: [],
    recommendations: [],
    prevention: [],
    conventionalCategoryEnglish: null,
    conventionalCategoryTamil: null,
    visibleParts: ["leaf"],
    needsExpertReview: false,
    explanationTamil: null,
    explanationEnglish: null,
    imageUrl: "file:///leaf.jpg",
    modelUsed: "controlled-test",
    testMode: null,
    verificationLevel: null,
    weatherSnapshot: null,
    latitude: null,
    longitude: null,
    language: "en",
    createdAt: new Date(Date.UTC(2026, 0, nextId)).toISOString(),
    ...overrides,
  };
}

describe("localDiseaseProvider history", () => {
  beforeEach(() => {
    nextId = 0;
    mockUserId = "user-a";
    diseaseStorage.clear();
    mockUserId = "user-b";
    diseaseStorage.clear();
    mockUserId = "user-a";
  });

  it("reads and deletes persisted reports", async () => {
    const stored = report();
    diseaseStorage.upsert(stored);

    const history = await localDiseaseProvider.listReports();
    expect(history.map((item) => item.id)).toEqual([stored.id]);
    expect((await localDiseaseProvider.getReport(stored.id)).symptoms).toEqual([
      "spots",
    ]);

    await localDiseaseProvider.deleteReport(stored.id);
    await expect(localDiseaseProvider.getReport(stored.id)).rejects.toThrow();
  });

  it("lists newest first", async () => {
    const older = report({ crop: "paddy" });
    const newer = report({ crop: "cotton" });
    diseaseStorage.upsert(older);
    diseaseStorage.upsert(newer);

    expect(
      (await localDiseaseProvider.listReports()).map((item) => item.id),
    ).toEqual([newer.id, older.id]);
  });

  it("filters history by farm", async () => {
    const farmA = report({ farmId: "farm-a" });
    diseaseStorage.upsert(farmA);
    diseaseStorage.upsert(report({ farmId: "farm-b" }));

    expect(
      (await localDiseaseProvider.listReports("farm-a")).map((item) => item.id),
    ).toEqual([farmA.id]);
  });

  it("keeps two farms isolated and exposes legacy reports only as unassigned", async () => {
    const farmA = report({ farmId: "farm-a" });
    const farmB = report({ farmId: "farm-b" });
    const unassigned = report({ farmId: null });
    diseaseStorage.upsert(farmA);
    diseaseStorage.upsert(farmB);
    diseaseStorage.upsert(unassigned);

    expect(
      (await localDiseaseProvider.listReports("farm-a")).map((item) => item.id),
    ).toEqual([farmA.id]);
    expect(
      (await localDiseaseProvider.listReports("farm-b")).map((item) => item.id),
    ).toEqual([farmB.id]);
    expect(
      (await localDiseaseProvider.listReports(null, true)).map(
        (item) => item.id,
      ),
    ).toEqual([unassigned.id]);
  });

  it("isolates locally cached reports by authenticated user", async () => {
    const userAReport = report({ farmId: "farm-a" });
    diseaseStorage.upsert(userAReport);

    mockUserId = "user-b";
    expect(await localDiseaseProvider.listReports()).toEqual([]);
    const userBReport = report({ farmId: "farm-b" });
    diseaseStorage.upsert(userBReport);

    expect(
      (await localDiseaseProvider.listReports()).map((item) => item.id),
    ).toEqual([userBReport.id]);
    mockUserId = "user-a";
    expect(
      (await localDiseaseProvider.listReports()).map((item) => item.id),
    ).toEqual([userAReport.id]);
  });

  it("fails closed when a farm cache envelope belongs to another user", async () => {
    const stored = report({ farmId: "farm-a" });
    appStorage.setJSON("agrowai.disease.reports:user-a:farm-a", {
      ownerUserId: "user-b",
      farmId: "farm-a",
      reports: [stored],
    });
    appStorage.setJSON("agrowai.disease.reports:user-a:farm-index", ["farm-a"]);

    expect(await localDiseaseProvider.listReports()).toEqual([]);
  });

  it("does not expose cached reports while signed out", async () => {
    diseaseStorage.upsert(report({ farmId: "farm-a" }));
    mockUserId = "";

    expect(await localDiseaseProvider.listReports()).toEqual([]);
  });
});
