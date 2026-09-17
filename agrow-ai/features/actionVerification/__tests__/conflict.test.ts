import { appStorage } from "@/lib/storage";
import { ApiError } from "@/types";
import { api } from "@/services/apiClient";
import {
  getActionConflicts,
  resolveActionConflict,
  syncActionOutbox,
  listActions,
} from "../api";

jest.mock("@/services/apiClient", () => ({
  api: { get: jest.fn(), post: jest.fn() },
}));
jest.mock("@/features/auth/store/authStore", () => ({
  useAuthStore: { getState: () => ({ user: { id: "user-1" } }) },
}));

it("retains a version conflict until the farmer resolves it", async () => {
  appStorage.setJSON("agrowai.action-verification.outbox.user-1", [
    {
      actionId: "a1",
      event: "done",
      expectedVersion: 1,
      idempotencyKey: "request-123",
    },
  ]);
  (api.post as jest.Mock).mockRejectedValue(
    new ApiError({
      message: "conflict",
      status: 409,
      errorCode: "ACTION_VERSION_CONFLICT",
    }),
  );
  expect(await syncActionOutbox()).toBe(0);
  expect(getActionConflicts()).toHaveLength(1);
  const current = {
    id: "a1",
    farm_id: "f1",
    crop_cycle_id: null,
    source_feature: "weather_to_action",
    source_record_id: "w1",
    source_version: "1",
    action_code: "Check drainage",
    source_verified: false,
    farmer_created: false,
    suggestion_time: "2026-08-15T00:00:00Z",
    due_at: null,
    expires_at: null,
    status: "farmer_reported_done",
    verification_scope: "workflow_completion_only",
    version: 3,
    pending_sync: false,
    created_at: "2026-08-15T00:00:00Z",
    updated_at: "2026-08-15T00:00:00Z",
  };
  (api.get as jest.Mock).mockResolvedValue({
    ...current,
    status: "suggested",
    version: 2,
  });
  (api.post as jest.Mock).mockResolvedValue(current);
  await resolveActionConflict("a1", "apply_mine");
  expect(getActionConflicts()).toHaveLength(0);
});

it("retains offline responses instead of counting local queueing as sync", async () => {
  const input = { actionId: "offline", event: "done", expectedVersion: 1, idempotencyKey: "offline-1" };
  appStorage.setJSON("agrowai.action-verification.outbox.user-1", [input]);
  appStorage.setJSON("agrowai.action-verification.cache.user-1", [{ id: "offline", status: "suggested", version: 1 }]);
  (api.post as jest.Mock).mockRejectedValue(new ApiError({ message: "offline", status: 0, errorCode: "NETWORK_ERROR" }));
  expect(await syncActionOutbox()).toBe(0);
  expect(appStorage.getJSON("agrowai.action-verification.outbox.user-1")).toEqual([input]);
});

it("reports a first-load network error instead of a false empty list", async () => {
  appStorage.remove("agrowai.action-verification.cache.user-1");
  const error = new ApiError({ message: "offline", status: 0, errorCode: "NETWORK_ERROR" });
  (api.get as jest.Mock).mockRejectedValue(error);
  await expect(listActions()).rejects.toBe(error);
});

it("preserves new responses queued while syncing", async () => {
  const original = { actionId: "a1", event: "done", expectedVersion: 1, idempotencyKey: "old" };
  const added = { ...original, idempotencyKey: "new" };
  appStorage.setJSON("agrowai.action-verification.outbox.user-1", [original]);
  (api.post as jest.Mock).mockImplementation(async () => {
    appStorage.setJSON("agrowai.action-verification.outbox.user-1", [original, added]);
    return { id: "a1", pending_sync: false };
  });
  expect(await syncActionOutbox()).toBe(1);
  expect(appStorage.getJSON("agrowai.action-verification.outbox.user-1")).toEqual([added]);
});

it("keeps a conflict resolution queued when its POST loses connection", async () => {
  const input = { actionId: "a1", event: "done", expectedVersion: 1, idempotencyKey: "conflict-offline" };
  appStorage.setJSON("agrowai.action-verification.outbox.user-1", [input]);
  appStorage.setJSON("agrowai.action-verification.conflicts.user-1", [{ input, detectedAt: "2026-09-01" }]);
  appStorage.setJSON("agrowai.action-verification.cache.user-1", [{ id: "a1", version: 1, status: "suggested" }]);
  (api.get as jest.Mock).mockResolvedValue({ id: "a1", version: 2, status: "suggested" });
  (api.post as jest.Mock).mockRejectedValue(new ApiError({ status: 0, message: "offline", errorCode: "NETWORK_ERROR" }));
  expect((await resolveActionConflict("a1", "apply_mine")).pendingSync).toBe(true);
  expect(appStorage.getJSON("agrowai.action-verification.outbox.user-1")).toEqual([
    { ...input, expectedVersion: 2, idempotencyKey: "conflict-offline-resolved" },
  ]);
});
