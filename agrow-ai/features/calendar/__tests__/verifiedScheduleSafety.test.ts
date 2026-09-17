import { getSchedule } from "../services/schedules";
import { localCalendarProvider } from "../services/localCalendarProvider";

describe("verified crop schedule safety", () => {
  it("does not inherit a generic or legacy paddy schedule", () => {
    expect(getSchedule("unknown")).toEqual([]);
    expect(getSchedule("paddy")).toEqual([]);
  });

  it("returns STAGE_DATA_UNAVAILABLE instead of generating local advice", async () => {
    await expect(
      localCalendarProvider.generate({
        farmId: "farm-1",
        crop: "paddy",
        sowingDate: "2026-08-01",
      }),
    ).rejects.toMatchObject({ code: "STAGE_DATA_UNAVAILABLE" });
  });
});
