const React = require("react");
const TestRenderer = require("react-test-renderer");
const mockPush = jest.fn();
jest.mock("expo-router", () => ({ useRouter: () => ({ push: mockPush }) }));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({ colors: { primary: "#008800", card: "#151A16" } }),
}));
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});
jest.mock("@/components/ui", () => {
  const MockReact = require("react");
  const { Pressable, Text } = require("react-native");
  return {
    AgText: Text,
    AgPressable: (props: any) => MockReact.createElement(Pressable, props),
  };
});
import {
  buildQuickActionRows,
  QUICK_ACTIONS,
  QuickActions,
} from "../components/QuickActions";
import { HOME_FEATURE_ROUTES } from "../routes";
import { ta } from "../../../localization/locales/ta";

test("Home shows the approved quick actions", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(React.createElement(QuickActions));
  });
  expect(
    tree.root.findByProps({ accessibilityLabel: "home.actionPlantIdentifier" }),
  ).toBeTruthy();
  for (const key of [
    "home.actionAI",
    "home.actionDisease",
    "weather.title",
    "home.actionAddFarm",
    "home.actionCalendar",
    "home.actionGrowth",
    "home.actionMarket",
    "home.actionSchemes",
    "home.actionSell",
    "notifications.title",
    "home.actionPlantIdentifier",
    "home.actionSoil",
    "home.actionNutrient",
    "home.actionSatellite",
    // intelligence/memory have real, working screens + a real backend but
    // had no Home entry anywhere in the app -- a missed wiring line, not a
    // deliberate hold-back (2026-08 pre-release audit) -- so they're now
    // shown unconditionally, unlike the internalFeatureTesting-gated set
    // below.
    "intelligence.title",
    "memory.title",
    // The offline crop field guide is complete and low-risk (no AI
    // involved) -- unhidden per explicit product decision, 2026-08
    // pre-release audit follow-up. Unlike intelligence/memory this one
    // required an actual product call rather than being an oversight.
    "home.actionOfflineKnowledge",
  ]) {
    expect(tree.root.findByProps({ accessibilityLabel: key })).toBeTruthy();
  }
  for (const hidden of [
    "home.actionCropRecommendation",
    "home.actionEquipment",
    "home.actionCommunity",
    // Gated behind internalFeatureTesting alongside the above -- the
    // production expert roster isn't populated/verified yet (2026-08
    // pre-release audit); was previously shown unconditionally by mistake.
    "home.actionExperts",
  ]) {
    expect(
      tree.root.findAllByProps({ accessibilityLabel: hidden }),
    ).toHaveLength(0);
  }
});

test("keeps the row builder stable for callers that request two columns", () => {
  const rows = buildQuickActionRows(QUICK_ACTIONS, 2);
  expect(rows.flat()).toEqual(QUICK_ACTIONS);
  expect(rows.every((row) => row.length <= 2)).toBe(true);
  expect(
    buildQuickActionRows(QUICK_ACTIONS.slice(0, 3)).map((row) => row.length),
  ).toEqual([2, 1]);
});

test("can collapse to one column without dropping or reordering tools", () => {
  const rows = buildQuickActionRows(QUICK_ACTIONS, 1);
  expect(rows).toHaveLength(QUICK_ACTIONS.length);
  expect(rows.flat()).toEqual(QUICK_ACTIONS);
});

test("renders one full-width card per row and preserves every existing route and tap action", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(React.createElement(QuickActions));
  });

  const rowCount = QUICK_ACTIONS.length;
  for (let index = 0; index < rowCount; index += 1) {
    expect(
      tree.root.findByProps({ testID: `quick-access-row-${index}` }),
    ).toBeTruthy();
  }

  expect(
    tree.root.findByProps({ accessibilityLabel: "quick-access-grid-1-column" }),
  ).toBeTruthy();

  for (const action of QUICK_ACTIONS) {
    const card = tree.root.findByProps({
      testID: `quick-action-${action.key}`,
    });
    await TestRenderer.act(async () => {
      card.props.onPress();
    });
    expect(mockPush).toHaveBeenLastCalledWith(HOME_FEATURE_ROUTES[action.key]);
  }
});

test("renders every tool as a bordered horizontal card with its arrow pinned right", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(React.createElement(QuickActions));
  });

  const card = tree.root.findByProps({ testID: "quick-action-weather" });
  const cardStyle = Object.assign({}, ...card.props.style.filter(Boolean));
  expect(cardStyle).toMatchObject({
    width: "100%",
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    backgroundColor: "#FFFDF8",
  });

  const arrowContainer = card.findAllByType(require("react-native").View).find(
    (node: any) => {
      const style = Object.assign(
        {},
        ...(Array.isArray(node.props.style)
          ? node.props.style.filter(Boolean)
          : [node.props.style].filter(Boolean)),
      );
      return style.marginLeft === "auto" && style.flexShrink === 0;
    },
  );
  expect(arrowContainer).toBeTruthy();
});

test("provides localized header, subtitle, and Tamil-ready helper keys", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(React.createElement(QuickActions));
  });
  expect(
    tree.root.findAllByProps({ children: "home.quickAccess" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "home.quickAccessSubtitle" }),
  ).not.toHaveLength(0);
  for (const action of QUICK_ACTIONS) {
    expect(action.subtitleKey).toMatch(/^home\..+Description$/);
    const localeKey = action.subtitleKey.replace(
      "home.",
      "",
    ) as keyof typeof ta.home;
    expect(ta.home[localeKey]).toBeTruthy();
  }
});
