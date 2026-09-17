/**
 * API envelope types — must match docs/API_CONTRACT.md exactly.
 * Every backend response is wrapped in one of these shapes.
 */
export interface ApiSuccess<T> {
  success: true;
  message: string;
  data: T;
  timestamp: string;
  request_id: string;
}

export interface ApiFieldError {
  field?: string;
  message: string;
}

export interface ApiErrorEnvelope {
  success: false;
  message: string;
  error_code: string;
  errors: ApiFieldError[];
  timestamp: string;
  request_id: string;
}

/** Normalised error thrown by the API client for callers to handle. */
export class ApiError extends Error {
  status: number;
  errorCode: string;
  errors: ApiFieldError[];
  requestId?: string;
  /** Optional small string map from the backend for building a more specific,
   * localized message than `message` alone (e.g. which crop was expected vs
   * observed on a nutrient-analysis crop mismatch). Absent for most errors. */
  details?: Record<string, string>;

  constructor(params: {
    status: number;
    message: string;
    errorCode: string;
    errors?: ApiFieldError[];
    requestId?: string;
    details?: Record<string, string>;
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.status = params.status;
    this.errorCode = params.errorCode;
    this.errors = params.errors ?? [];
    this.requestId = params.requestId;
    this.details = params.details;
  }

  get isNetwork() {
    return this.status === 0;
  }
  /** True only for a client-side request timeout, not a genuine offline/DNS
   * failure — both collapse to status 0 in axios, but the error `code`
   * still tells them apart (see services/apiClient.ts). */
  get isTimeout() {
    return this.errorCode === 'timeout_error';
  }
  get isAuth() {
    return this.status === 401 || this.status === 403;
  }
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}
