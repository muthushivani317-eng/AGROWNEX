import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';

import { env } from '@/config/env';
import { getLanguage } from '@/localization';
import { logger } from '@/lib/logger';
import { ApiError, type ApiSuccess } from '@/types';
import { uuid } from '@/utils/id';

/**
 * Single HTTP entry point (docs/FRONTEND_ARCHITECTURE.md → API LAYER).
 * Screens never call fetch/axios directly — they go through feature services,
 * which use these helpers. Handles auth, request IDs, language, retry, logging,
 * and unwraps the standard API envelope (docs/API_CONTRACT.md).
 */

type TokenProvider = () => string | null | Promise<string | null>;
/** Attempt a token refresh; return the new id token, or null if unrenewable. */
type TokenRefresher = () => Promise<string | null>;

let getToken: TokenProvider = () => null;
let refreshSession: TokenRefresher = async () => null;
let onUnauthorized: () => void = () => {};

/** Wire the auth layer to the client without creating an import cycle. */
export function configureApiAuth(opts: {
  getToken: TokenProvider;
  refreshSession: TokenRefresher;
  onUnauthorized: () => void;
}) {
  getToken = opts.getToken;
  refreshSession = opts.refreshSession;
  onUnauthorized = opts.onUnauthorized;
}

const RETRY_LIMIT = 2;
const EXPECTED_ERROR_CODES = new Set(['ai_daily_quota_exceeded', 'growth_session_not_found', 'supplier_profile_not_found']);
const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504]);

interface RetryConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
  _refreshed?: boolean;
  _skipRetry?: boolean;
}

export const httpClient: AxiosInstance = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.apiTimeoutMs,
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
});

httpClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = await getToken();
    if (token) config.headers.set('Authorization', `Bearer ${token}`);
    config.headers.set(
      'Accept-Language',
      getLanguage() === 'ta' ? 'ta-IN' : 'en-IN',
    );
    config.headers.set('X-Request-ID', uuid());
    // Axios serializes FormData as JSON when an inherited JSON content type is
    // present. Leave multipart headers to the native transport so it adds the
    // required boundary for every image upload.
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      config.headers.delete('Content-Type');
    }
    return config;
  },
);

httpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined;
    const status = error.response?.status ?? 0;

    // On 401, try a single token refresh then replay the request once
    // (docs/SECURITY.md → token refresh / session expiry). If refresh fails,
    // hand off to the unauthorized handler (which signs the user out).
    if (status === 401 && config && !config._refreshed) {
      config._refreshed = true;
      const newToken = await refreshSession();
      if (newToken) {
        config.headers.set('Authorization', `Bearer ${newToken}`);
        return httpClient(config);
      }
      onUnauthorized();
    } else if (status === 401) {
      onUnauthorized();
    }

    // Retry transient failures (network / 5xx / throttling) with backoff.
    const isRetryable = status === 0 || RETRYABLE_STATUS.has(status);
    if (config && isRetryable && !config._skipRetry) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      if (config._retryCount <= RETRY_LIMIT) {
        const delay = Math.min(500 * 2 ** config._retryCount, 8000);
        await new Promise((r) => setTimeout(r, delay));
        return httpClient(config);
      }
    }

    const body = error.response?.data as
      | {
          message?: string;
          error_code?: string;
          errors?: unknown;
          request_id?: string;
          detail?: { code?: string };
          details?: Record<string, string>;
        }
      | undefined;

    const apiError = new ApiError({
      status,
      message: body?.message ?? error.message ?? 'Request failed',
      errorCode:
        body?.error_code ??
        body?.detail?.code ??
        (status === 0
          ? error.code === 'ECONNABORTED'
            ? 'timeout_error'
            : 'network_error'
          : 'http_error'),
      errors: Array.isArray(body?.errors) ? (body!.errors as never[]) : [],
      requestId: body?.request_id,
      details:
        body?.details && typeof body.details === 'object' ? body.details : undefined,
    });

    // Expected outcomes, not bugs: log as warn so they don't raise a red error box.
    // (quota reached; no growth session yet before the first growth photo)
    if (EXPECTED_ERROR_CODES.has(apiError.errorCode)) {
      logger.warn('api', apiError.status, apiError.errorCode);
    } else {
      logger.error('api', apiError.status, apiError.errorCode, apiError.message);
    }
    return Promise.reject(apiError);
  },
);

/** Unwrap the `{ success, data }` envelope, returning just `data`. */
async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const res = await httpClient.request<ApiSuccess<T>>(config);
  return res.data.data;
}

export const api = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'GET', url }),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'POST', url, data }),
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'PUT', url, data }),
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'PATCH', url, data }),
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    request<T>({ ...config, method: 'DELETE', url }),
};
