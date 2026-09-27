// Admin sessions auto sign out 15 minutes after sign-in. The API refuses
// sensitive admin actions once the sign-in is older than 15 minutes
// (admin_recent_auth_required), so signing out on time is better than
// letting the admin hit a 403 in the middle of a task.
const KEY = 'agrownex_admin_signed_in_at';
export const SESSION_MINUTES = 15;
export const REAUTH_EVENT = 'agrownex-admin-reauth-required';

export function markSignedIn(): void {
  try { localStorage.setItem(KEY, String(Date.now())); } catch { /* storage unavailable */ }
}

export function clearSignedIn(): void {
  try { localStorage.removeItem(KEY); } catch { /* storage unavailable */ }
}

/** Milliseconds left before auto sign-out; 0 when expired or unknown. */
export function msUntilSignOut(now = Date.now()): number {
  let raw: string | null = null;
  try { raw = localStorage.getItem(KEY); } catch { return 0; }
  const at = raw ? Number(raw) : NaN;
  if (!Number.isFinite(at)) return 0;
  return Math.max(0, at + SESSION_MINUTES * 60_000 - now);
}

/** Called by fetch wrappers when the API says the sign-in is too old. */
export function reportReauthRequired(): void {
  window.dispatchEvent(new Event(REAUTH_EVENT));
}
