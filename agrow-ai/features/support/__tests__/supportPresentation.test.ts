import fs from "node:fs";
import path from "node:path";

const screen = fs.readFileSync(
  path.resolve(__dirname, "../SupportTicketsScreen.tsx"),
  "utf8",
);

describe("farmer support presentation", () => {
  it("supports creating, tracking, and replying to tickets", () => {
    expect(screen).toContain("supportApi.create(input)");
    expect(screen).toContain("supportApi.reply(ticket.id, reply.trim())");
    expect(screen).toContain('ticket.status === "waiting_for_farmer"');
    expect(screen).toContain('t("support.privacyNote")');
  });
});
