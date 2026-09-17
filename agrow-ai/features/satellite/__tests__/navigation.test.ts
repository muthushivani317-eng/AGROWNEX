import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test("satellite route renders the current dashboard", () => {
  const route = readFileSync(
    resolve(process.cwd(), "app/satellite/index.tsx"),
    "utf8",
  );
  expect(route).toContain("SatelliteDashboardScreen");
  expect(route).toContain("export default SatelliteDashboardScreen");
});

test("satellite dashboard provides back navigation when opened from Home", () => {
  const screen = readFileSync(
    resolve(
      process.cwd(),
      "features/satellite/screens/SatelliteDashboardScreen.tsx",
    ),
    "utf8",
  );
  expect(screen).toContain("SatelliteBackHeader");
  expect(screen).toContain(
    '<SatelliteBackHeader title={t("satellite.title")} />',
  );
});

test("waterlogging has a reachable child route and back navigation", () => {
  const route = readFileSync(
    resolve(process.cwd(), "app/satellite/waterlogging.tsx"),
    "utf8",
  );
  const dashboard = readFileSync(
    resolve(
      process.cwd(),
      "features/satellite/screens/SatelliteDashboardScreen.tsx",
    ),
    "utf8",
  );
  const screen = readFileSync(
    resolve(process.cwd(), "features/satellite/screens/WaterloggingScreen.tsx"),
    "utf8",
  );
  expect(route).toContain("WaterloggingScreen");
  expect(dashboard).toContain("/satellite/waterlogging");
  expect(screen).toContain("SatelliteBackHeader");
  expect(screen).toContain("useWaterloggingAssessment");
  expect(screen).toContain("useWaterloggingHistory");
});

test("shared pressable has no Reanimated update surviving screen unmount", () => {
  const source = readFileSync(
    resolve(process.cwd(), "components/ui/AgPressable.tsx"),
    "utf8",
  );
  expect(source).not.toContain("react-native-reanimated");
  expect(source).not.toContain("useSharedValue");
  expect(source).not.toContain("withTiming");
});
