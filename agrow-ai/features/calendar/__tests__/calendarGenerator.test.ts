import { deriveSeason, generateEvents } from "../services/calendarGenerator";

describe("calendar generation safety", () => {
  it.each([null, "unknown", "paddy"])(
    "generates no generic or unverified schedule for %s",
    (crop) => {
      expect(
        generateEvents(
          { farmId: "farm-1", crop, sowingDate: "2026-06-15" },
          "2026-06-15T00:00:00.000Z",
        ),
      ).toEqual([]);
    },
  );

  it("keeps deterministic season display calculation separate from advice", () => {
    expect(deriveSeason("2026-07-01")).toBe("kharif");
    expect(deriveSeason("2026-11-01")).toBe("rabi");
    expect(deriveSeason("2026-03-01")).toBe("summer");
  });
});
