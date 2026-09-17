import fs from "node:fs";
import path from "node:path";

const screen = fs.readFileSync(
  path.resolve(__dirname, "..", "screens", "NotificationCenterScreen.tsx"),
  "utf8",
);
const card = fs.readFileSync(
  path.resolve(__dirname, "..", "components", "NotificationCard.tsx"),
  "utf8",
);
const filters = fs.readFileSync(
  path.resolve(__dirname, "..", "components", "NotificationFilters.tsx"),
  "utf8",
);
const en = fs.readFileSync(
  path.resolve(__dirname, "..", "..", "..", "localization", "locales", "en.ts"),
  "utf8",
);

describe("Notification Center redesign contract", () => {
  it("keeps real mark-read and mark-all-read mutations", () => {
    expect(screen).toContain("useMarkRead()");
    expect(screen).toContain("useMarkAllRead()");
    expect(screen).toContain("markRead.mutate(item.id,");
    expect(screen).toContain("markAllRead.mutate(undefined");
    expect(screen).toContain("notifications.actionFailed");
  });

  it("guards refresh, hides stale rows after failure and labels cached data", () => {
    expect(screen).toContain("refreshLock.current");
    expect(screen).toContain("query.isLoading || query.isError ? []");
    expect(screen).toContain("notifications.cachedNotice");
    expect(screen).not.toContain("<AgOfflineBanner");
  });

  it("calculates counts and filters from loaded model fields", () => {
    expect(screen).toContain("all: allItems.length");
    expect(screen).toContain("item.severity === 'info'");
    expect(screen).toContain("item.module === module");
    expect(filters).toContain("SEVERITIES.map");
    expect(filters).toContain("FILTERABLE_MODULES.map");
  });

  it("keeps detail navigation and only signals a modeled source action", () => {
    expect(screen).toContain("pathname: '/notifications/[id]'");
    expect(card).toContain("isValidActionRoute(item.actionRoute)");
  });

  it("removes unsafe scheme eligibility claims and requires official verification", () => {
    expect(en).toMatch(/title:\s*["']Potential scheme match["']/);
    expect(en).toContain("VERIFY AGAINST OFFICIAL SOURCE.");
    expect(en).not.toContain("title: 'You may be eligible'");
    expect(en).not.toContain("You may qualify for {{title}}");
  });
});
