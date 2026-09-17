export const STARTUP_PHASES = [
  'BOOTING',
  'STORAGE_INITIALIZING',
  'DATABASE_INITIALIZING',
  'AUTH_RESTORING',
  'ROUTE_RESOLVING',
  'READY',
  'RECOVERABLE_ERROR',
] as const;

export type StartupPhase = (typeof STARTUP_PHASES)[number];
export type StartupErrorCategory =
  | 'startup_timeout'
  | 'storage_initialization_failed'
  | 'database_initialization_failed'
  | 'auth_restoration_failed'
  | 'route_resolution_failed';

export interface StartupResult {
  phase: 'READY' | 'RECOVERABLE_ERROR';
  errorCategory: StartupErrorCategory | null;
}

export interface StartupOperations {
  initializeStorage: () => Promise<void>;
  initializeDatabase: () => Promise<void>;
  restoreAuth: () => Promise<void>;
  resolveRoute: () => Promise<void> | void;
}

export const STARTUP_TIMEOUT_MS = 15_000;

class StartupStepError extends Error {
  constructor(readonly category: StartupErrorCategory) {
    super(category);
  }
}

async function runStep(
  category: StartupErrorCategory,
  operation: () => Promise<void> | void,
): Promise<void> {
  try {
    await operation();
  } catch {
    throw new StartupStepError(category);
  }
}

export async function runStartupSequence(
  operations: StartupOperations,
  onPhase: (phase: StartupPhase) => void,
  timeoutMs = STARTUP_TIMEOUT_MS,
): Promise<StartupResult> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let settled = false;
  const emitPhase = (phase: StartupPhase) => {
    if (!settled) onPhase(phase);
  };
  const sequence = (async () => {
    emitPhase('STORAGE_INITIALIZING');
    await runStep('storage_initialization_failed', operations.initializeStorage);
    emitPhase('DATABASE_INITIALIZING');
    await runStep('database_initialization_failed', operations.initializeDatabase);
    emitPhase('AUTH_RESTORING');
    await runStep('auth_restoration_failed', operations.restoreAuth);
    emitPhase('ROUTE_RESOLVING');
    await runStep('route_resolution_failed', operations.resolveRoute);
    emitPhase('READY');
    return { phase: 'READY', errorCategory: null } as const;
  })();

  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new StartupStepError('startup_timeout')), timeoutMs);
  });

  try {
    const result = await Promise.race([sequence, timeout]);
    settled = true;
    return result;
  } catch (error) {
    settled = true;
    const category =
      error instanceof StartupStepError ? error.category : 'route_resolution_failed';
    onPhase('RECOVERABLE_ERROR');
    return { phase: 'RECOVERABLE_ERROR', errorCategory: category };
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export interface StartupRouteState {
  authStatus: 'initializing' | 'unauthenticated' | 'authenticated';
  languageSelected: boolean;
  hasOnboarded: boolean;
  profileCompleted: boolean;
}

export const STARTUP_ROUTES = [
  '/(auth)/language',
  '/(auth)/onboarding',
  '/(auth)/login',
  '/(auth)/complete-profile',
  '/(tabs)',
] as const;
export type StartupRoute = (typeof STARTUP_ROUTES)[number];

export function resolveStartupRoute(state: StartupRouteState): StartupRoute | null {
  if (state.authStatus === 'initializing') return null;
  if (state.authStatus === 'authenticated') {
    return state.profileCompleted ? '/(tabs)' : '/(auth)/complete-profile';
  }
  if (!state.languageSelected) return '/(auth)/language';
  return '/(auth)/login';
}

export function shouldReplaceStartupRoute({
  atIndex,
  inAuth,
  status,
  screen,
}: {
  atIndex: boolean;
  inAuth: boolean;
  status: StartupRouteState['authStatus'];
  screen?: string;
}): boolean {
  if (atIndex) return true;
  if (status === 'authenticated') return inAuth;
  return !inAuth || screen === 'complete-profile';
}
