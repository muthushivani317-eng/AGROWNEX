import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test("vegetation timeline uses explicit high-contrast colors on its light surface", () => {
  const screen = readFileSync(
    resolve(process.cwd(), "features/satellite/screens/SatelliteTimelineScreen.tsx"),
    "utf8",
  );
  const chart = readFileSync(
    resolve(process.cwd(), "features/satellite/components/TimelineChart.tsx"),
    "utf8",
  );

  expect(screen.match(/<AgChip/g)).toHaveLength(2);
  expect(screen.match(/\n\s+light\n/g)).toHaveLength(2);
  expect(chart).toContain("style={styles.title}");
  expect(chart).toContain("style={styles.axisLabel}");
  expect(chart).toContain("title: { color: SATELLITE_UI.text }");
  expect(chart).toContain("axisLabel: { color: SATELLITE_UI.muted }");
});
