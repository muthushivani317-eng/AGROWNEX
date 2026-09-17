const mockRecordError = jest.fn();
const mockLog = jest.fn();
const mockCrashlyticsInstance = { recordError: mockRecordError, log: mockLog };
const mockCrashlyticsFactory = jest.fn(() => mockCrashlyticsInstance);

let firebaseAuthErrorCategory: typeof import('../logger').firebaseAuthErrorCategory;
let logger: typeof import('../logger').logger;
let reportFirebaseAuthErrorCategory: typeof import('../logger').reportFirebaseAuthErrorCategory;

describe('logger -> Crashlytics forwarding', () => {
  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    mockCrashlyticsFactory.mockImplementation(() => mockCrashlyticsInstance);
    jest.doMock('@react-native-firebase/crashlytics', () => ({
      default: mockCrashlyticsFactory,
    }));
    jest.doMock('@/config/env', () => ({ isDev: false }));
    ({
      firebaseAuthErrorCategory,
      logger,
      reportFirebaseAuthErrorCategory,
    } = require('../logger'));
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(console, 'info').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('records the Error object and logs any extra args as a breadcrumb', () => {
    const error = new Error('boom');

    logger.error('ErrorBoundary', error, 'component stack here');

    expect(mockLog).toHaveBeenCalledWith('[ErrorBoundary] component stack here');
    expect(mockRecordError).toHaveBeenCalledWith(error, 'ErrorBoundary');
  });

  it('logs a breadcrumb without recordError when no Error object is present', () => {
    logger.error('startup_configuration', 'missing config');

    expect(mockLog).toHaveBeenCalledWith('[startup_configuration] missing config');
    expect(mockRecordError).not.toHaveBeenCalled();
  });

  it('does not touch Crashlytics for info/warn/debug logs', () => {
    logger.info('scope', 'hello');
    logger.warn('scope', 'careful');

    expect(mockCrashlyticsFactory).not.toHaveBeenCalled();
  });

  it('never throws even if the native Crashlytics module misbehaves', () => {
    mockRecordError.mockImplementation(() => {
      throw new Error('native module RNFBCrashlyticsModule not found');
    });

    expect(() => logger.error('scope', new Error('boom'))).not.toThrow();
  });

  it('reports only a sanitized Firebase auth error category', () => {
    reportFirebaseAuthErrorCategory('sendOtp', 'auth/billing-not-enabled');

    expect(mockRecordError).toHaveBeenCalledTimes(1);
    const [error, scope] = mockRecordError.mock.calls[0];
    expect(scope).toBe('firebaseAuth.sendOtp');
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe('firebase_auth_category:auth/billing-not-enabled');
    expect(JSON.stringify(mockRecordError.mock.calls)).not.toContain('+91');
    expect(JSON.stringify(mockRecordError.mock.calls)).not.toContain('otp');
    expect(JSON.stringify(mockRecordError.mock.calls)).not.toContain('token');
  });

  it('collapses an unsafe native error code to unknown', () => {
    const category = reportFirebaseAuthErrorCategory(
      'confirmOtp',
      'auth/bad phone=+919876543210 token=secret',
    );

    const [error] = mockRecordError.mock.calls[0];
    expect(category).toBe('unknown');
    expect(error.message).toBe('firebase_auth_category:unknown');
  });

  it.each([
    'auth/otp-123456',
    'auth/token-secretvalue',
    'auth/phone-919876543210',
  ])('rejects shape-valid but unrecognized sensitive category %s', (unsafeCode) => {
    const category = reportFirebaseAuthErrorCategory('sendOtp', unsafeCode);
    const [error] = mockRecordError.mock.calls[0];

    expect(category).toBe('unknown');
    expect(error.message).toBe('firebase_auth_category:unknown');
    expect(JSON.stringify(mockRecordError.mock.calls)).not.toContain(unsafeCode);
  });

  it('sanitizes refresh categories without forwarding arbitrary identifiers', () => {
    expect(firebaseAuthErrorCategory('auth/user-token-expired')).toBe(
      'auth/user-token-expired',
    );
    expect(firebaseAuthErrorCategory('auth/token-secretvalue')).toBe('unknown');
  });

  it('classifies only the fixed invalid-reCAPTCHA failure signature without retaining its message', () => {
    expect(firebaseAuthErrorCategory(
      'auth/unknown',
      '[auth/unknown] The request contains an invalid reCAPTCHA token.',
    )).toBe('auth/invalid-recaptcha-token');
    expect(firebaseAuthErrorCategory('auth/unknown', 'arbitrary native failure')).toBe('unknown');
  });

  it('reports the invalid-reCAPTCHA category without forwarding the native message', () => {
    const nativeMessage =
      'The request contains an invalid reCAPTCHA token. phone=+919876543210 otp=123456';

    const category = reportFirebaseAuthErrorCategory(
      'sendOtp',
      'auth/unknown',
      nativeMessage,
    );

    expect(category).toBe('auth/invalid-recaptcha-token');
    const [reportedError] = mockRecordError.mock.calls[0];
    expect(reportedError.message).toBe(
      'firebase_auth_category:auth/invalid-recaptcha-token',
    );
    expect(JSON.stringify(mockRecordError.mock.calls)).not.toContain('+919876543210');
    expect(JSON.stringify(mockRecordError.mock.calls)).not.toContain('123456');
  });
});
