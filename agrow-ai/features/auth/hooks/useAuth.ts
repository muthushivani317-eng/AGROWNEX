import { useAuthStore } from '../store/authStore';

/** Read-only view of the current auth session. */
export function useAuth() {
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const hasOnboarded = useAuthStore((s) => s.hasOnboarded);

  return {
    status,
    user,
    hasOnboarded,
    isInitializing: status === 'initializing',
    isAuthenticated: status === 'authenticated',
    needsProfile: status === 'authenticated' && !user?.profileCompleted,
  };
}
