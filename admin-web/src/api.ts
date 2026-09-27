import { getConfig } from './config';
import type { Envelope } from './types';

let csrfToken: string | null = null;
export const getCsrfToken = () => csrfToken;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase();
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, {
    ...init,
    credentials: 'include',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(method !== 'GET' && method !== 'HEAD' && csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      ...init.headers
    }
  });
  const nextCsrf = response.headers.get('X-CSRF-Token');
  if (nextCsrf) csrfToken = nextCsrf;
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: { message?: string } | string; message?: string; error_code?: string } | null;
    const detail = typeof body?.detail === 'string' ? body.detail : body?.detail?.message;
    const friendly = body?.error_code === 'admin_recent_auth_required'
      ? 'For security, sign out and sign in again, then retry within 15 minutes.'
      : undefined;
    throw new ApiError(response.status, friendly ?? detail ?? body?.message ?? (response.status === 403 ? 'Access denied.' : 'Request failed.'));
  }
  const body = await response.json() as Envelope<T>;
  return body.data;
}
