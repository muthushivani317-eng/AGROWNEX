import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test("waterlogging uses fixed high-contrast colors on light surfaces", () => {
  const screen = readFileSync(
    resolve(process.cwd(), "features/satellite/screens/WaterloggingScreen.tsx"),
    "utf8",
  );

  expect(screen).toContain("style={styles.resultTitle}");
  expect(screen).toContain("style={styles.resultGuidance}");
  expect(screen).toContain("style={styles.resultMeta}");
  expect(screen).toContain("resultTitle: { color: SATELLITE_UI.text }");
  expect(screen).toContain(
    'resultMeta: { color: "#43564D", lineHeight: 20 }',
  );
  expect(screen).toContain("<LatestImageCard");
  expect(screen).toContain("<SatelliteImageViewer");
  expect(screen).toContain('t("satellite.waterlogging.reviewReason")');
  expect(screen).not.toContain('color="muted"');
  expect(screen).not.toContain("useAppTheme");
});
