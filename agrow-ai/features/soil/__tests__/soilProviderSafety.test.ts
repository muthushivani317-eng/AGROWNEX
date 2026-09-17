describe("soil provider release safety", () => {
  beforeEach(() => {
    jest.resetModules();
  });

  it("uses an unavailable provider in production when the backend is absent", async () => {
    jest.doMock("@/config/env", () => ({
      isBackendConfigured: false,
      buildProfile: "production",
    }));
    jest.doMock("@/lib/logger", () => ({ logger: { info: jest.fn() } }));

    const { getSoilProvider } = require("../services/soilProvider");
    const provider = getSoilProvider();

    await expect(provider.dashboard("farm-1")).rejects.toMatchObject({
      code: "remote_estimation_unavailable",
    });
  });
});
