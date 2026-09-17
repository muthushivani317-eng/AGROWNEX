import {
  resolveStartupRoute,
  runStartupSequence,
  STARTUP_ROUTES,
  type StartupPhase,
} from '../startupStateMachine';

const ok = () => Promise.resolve();

describe('deterministic startup state machine', () => {
  it('runs every phase in order and reaches READY', async () => {
    const phases: StartupPhase[] = [];
    const result = await runStartupSequence(
      { initializeStorage: ok, initializeDatabase: ok, restoreAuth: ok, resolveRoute: ok },
      (phase) => phases.push(phase),
    );
    expect(result).toEqual({ phase: 'READY', errorCategory: null });
    expect(phases).toEqual([
      'STORAGE_INITIALIZING',
      'DATABASE_INITIALIZING',
      'AUTH_RESTORING',
      'ROUTE_RESOLVING',
      'READY',
    ]);
  });

  it.each([
    ['initializeDatabase', 'database_initialization_failed'],
    ['restoreAuth', 'auth_restoration_failed'],
    ['resolveRoute', 'route_resolution_failed'],
  ] as const)('turns %s failure into a visible recoverable state', async (step, category) => {
    const operations = { initializeStorage: ok, initializeDatabase: ok, restoreAuth: ok, resolveRoute: ok };
    operations[step] = () => Promise.reject(new Error('private detail must not escape'));
    await expect(runStartupSequence(operations, () => {})).resolves.toEqual({
      phase: 'RECOVERABLE_ERROR',
      errorCategory: category,
    });
  });

  it('times out a stuck operation rather than waiting forever', async () => {
    const never = () => new Promise<void>(() => {});
    await expect(
      runStartupSequence(
        { initializeStorage: never, initializeDatabase: ok, restoreAuth: ok, resolveRoute: ok },
        () => {},
        5,
      ),
    ).resolves.toEqual({ phase: 'RECOVERABLE_ERROR', errorCategory: 'startup_timeout' });
  });

  it('does not allow late async completion to replace a timeout error', async () => {
    const phases: StartupPhase[] = [];
    let finishStorage!: () => void;
    const storage = new Promise<void>((resolve) => {
      finishStorage = resolve;
    });
    const result = await runStartupSequence(
      {
        initializeStorage: () => storage,
        initializeDatabase: ok,
        restoreAuth: ok,
        resolveRoute: ok,
      },
      (phase) => phases.push(phase),
      5,
    );
    finishStorage();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(result).toEqual({ phase: 'RECOVERABLE_ERROR', errorCategory: 'startup_timeout' });
    expect(phases).toEqual(['STORAGE_INITIALIZING', 'RECOVERABLE_ERROR']);
  });
});

describe('single startup route resolver', () => {
  it.each([
    [{ authStatus: 'unauthenticated', languageSelected: false, hasOnboarded: false, profileCompleted: false }, '/(auth)/language'],
    [{ authStatus: 'unauthenticated', languageSelected: true, hasOnboarded: false, profileCompleted: false }, '/(auth)/login'],
    [{ authStatus: 'unauthenticated', languageSelected: true, hasOnboarded: true, profileCompleted: false }, '/(auth)/login'],
    [{ authStatus: 'authenticated', languageSelected: true, hasOnboarded: true, profileCompleted: false }, '/(auth)/complete-profile'],
    [{ authStatus: 'authenticated', languageSelected: true, hasOnboarded: true, profileCompleted: true }, '/(tabs)'],
  ] as const)('resolves persisted state to an existing registered route', (state, target) => {
    expect(resolveStartupRoute(state)).toBe(target);
    expect(STARTUP_ROUTES).toContain(target);
  });

  it('does not redirect while auth is still initializing', () => {
    expect(resolveStartupRoute({ authStatus: 'initializing', languageSelected: false, hasOnboarded: false, profileCompleted: false })).toBeNull();
  });
});
