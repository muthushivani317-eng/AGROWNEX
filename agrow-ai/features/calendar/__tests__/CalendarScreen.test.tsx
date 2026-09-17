const React = require("react");
const TestRenderer = require("react-test-renderer");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { count?: number }) =>
      options?.count == null ? key : `${key}:${options.count}`,
  }),
}));
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({
    colors: {
      primary: "#4CAF50",
      primaryLight: "#81C784",
      success: "#66BB6A",
      info: "#42A5F5",
      danger: "#EF5350",
      warning: "#FFCA28",
      card: "#252525",
      surface: "#1E1E1E",
      border: "#333333",
      text: "#FFFFFF",
      textMuted: "#BDBDBD",
    },
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

import fs from "node:fs";
import path from "node:path";

import { CalendarProgress } from "../components/CalendarProgress";
import { ViewTabs } from "../components/ViewTabs";

const screenSource = fs.readFileSync(
  path.resolve(__dirname, "..", "screens", "CalendarScreen.tsx"),
  "utf8",
);
const english = fs.readFileSync(
  path.resolve(__dirname, "..", "..", "..", "localization", "locales", "en.ts"),
  "utf8",
);
const tamil = fs.readFileSync(
  path.resolve(__dirname, "..", "..", "..", "localization", "locales", "ta.ts"),
  "utf8",
);

describe("Crop Calendar redesign", () => {
  it("distinguishes an empty view from an absent calendar and refreshes all dependencies", () => {
    expect(screenSource).toContain('events.length === 0 && summary?.total === 0');
    expect(screenSource).toContain('farmQuery.refetch(), refetch(), refetchSummary()');
    expect(screenSource).toContain('generate.isError || update.isError');
    expect(screenSource).toContain('data={isError ? [] : displayed}');
  });
  it("renders real provider summary counts and does not add mock progress values", async () => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(CalendarProgress, {
          summary: {
            farmId: "farm-1",
            crop: "paddy",
            season: "kharif",
            total: 7,
            completed: 2,
            pending: 4,
            missed: 1,
            skipped: 0,
          },
        }),
      );
    });
    const text = tree.root
      .findAllByType(require("react-native").Text)
      .map((node: any) => node.props.children)
      .flat(Infinity);
    expect(text).toEqual(expect.arrayContaining([2, 4, 1, 7]));
    expect(screenSource).not.toMatch(
      /(?:completed|pending|missed|total):\s*(?:14|30)/,
    );
  });

  it("keeps every implemented filter separate and functional", async () => {
    const onChange = jest.fn();
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(
        React.createElement(ViewTabs, { active: "today", onChange }),
      );
    });
    for (const view of [
      "today",
      "upcoming",
      "timeline",
      "month",
      "completed",
    ]) {
      expect(
        tree.root.findAllByProps({ testID: `calendar-view-${view}` }).length,
      ).toBeGreaterThan(0);
    }
    const upcoming = tree.root
      .findAllByProps({ testID: "calendar-view-upcoming" })
      .find((node: any) => typeof node.props.onPress === "function");
    await TestRenderer.act(async () => upcoming.props.onPress());
    expect(onChange).toHaveBeenCalledWith("upcoming");
  });

  it("preserves refresh, completion, loading, error, and empty-state behavior", () => {
    expect(screenSource).toContain("onPress={onGenerate}");
    expect(screenSource).toContain(
      'event.status === "done" ? "pending" : "done"',
    );
    expect(screenSource).toContain("isLoading ?");
    expect(screenSource).toContain("isError ?");
    expect(screenSource).toContain("<AgEmptyState");
  });

  it("adds matching English and Tamil keys and no unsupported in-progress state", () => {
    for (const key of [
      "subtitle",
      "activitiesHeading",
      "officialGuidance",
      "tipMessage",
      "cachedNotice",
    ]) {
      expect(english).toContain(`${key}:`);
      expect(tamil).toContain(`${key}:`);
    }
    expect(screenSource).not.toContain("in_progress");
    expect(screenSource).not.toContain("In Progress");
  });

  it("keeps light calendar surfaces readable in dark app theme", () => {
    const tabsSource = fs.readFileSync(
      path.resolve(__dirname, "..", "components", "ViewTabs.tsx"),
      "utf8",
    );
    const farmsSource = fs.readFileSync(
      path.resolve(__dirname, "..", "components", "FarmSwitcher.tsx"),
      "utf8",
    );

    expect(screenSource).toContain("<AgErrorState light");
    expect(screenSource).toContain("<AgEmptyState\n          light");
    expect(screenSource).not.toContain('color="muted"');
    expect(tabsSource).toContain('color: selected ? "#0F5A2D"');
    expect(tabsSource).toContain("row: { gap: 8");
    expect(tabsSource).toContain("<TouchableOpacity");
    expect(tabsSource).not.toContain("style={({ pressed })");
    expect(farmsSource).toContain('color: selected ? "#0F5A2D"');
    expect(farmsSource).toContain("<TouchableOpacity");
    expect(farmsSource).not.toContain("style={({ pressed })");
  });
});
