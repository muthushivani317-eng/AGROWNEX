import { QueryClient } from '@tanstack/react-query';

/**
 * Shared React Query client. Server state lives here — never in Zustand
 * (docs/FRONTEND_ARCHITECTURE.md). Defaults are tuned for flaky rural
 * connectivity: generous stale time, capped retries with backoff, and no
 * aggressive refetching that would burn mobile data.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 min
      gcTime: 1000 * 60 * 60 * 24, // 24 h
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30_000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: { retry: 1 },
  },
});
