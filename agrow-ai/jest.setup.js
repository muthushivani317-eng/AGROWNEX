/* eslint-disable no-undef */

// jest-expo's bundled mock for the native "ExpoObserve" module (jest-expo@57.0.3:
// node_modules/jest-expo/src/preset/moduleMocks/expoModules.js) only stubs
// addListener/configure/dispatchEvents/removeListeners/setBundleDefaults. It
// predates expo-observe 57.0.10's `getIntegrations()` method, which expo-image@57
// calls unconditionally at import time (node_modules/expo-image/src/index.ts ->
// observe.ts:159 `activate(state, observe.getIntegrations())`). Without this
// patch, merely doing `import { Image } from 'expo-image'` anywhere in the
// module graph of a test file crashes with "observe.getIntegrations is not a
// function" -- confirmed via GeneralDiagnosisScreen.tsx (2026-08 pre-release
// audit). This wraps the real `requireOptionalNativeModule` (still backed by
// jest-expo's native-module mocking underneath) and fills in the one missing
// method with a harmless no-integrations stub, rather than forking jest-expo
// or hand-mocking all of expo-image.
jest.mock('expo', () => {
  const actualExpo = jest.requireActual('expo');
  return {
    ...actualExpo,
    requireOptionalNativeModule: (name) => {
      const nativeModule = actualExpo.requireOptionalNativeModule(name);
      if (
        name === 'ExpoObserve' &&
        nativeModule &&
        typeof nativeModule.getIntegrations !== 'function'
      ) {
        return { ...nativeModule, getIntegrations: () => ({}) };
      }
      return nativeModule;
    },
  };
});

// In-memory MMKV mock (no native module in Jest).
jest.mock('react-native-mmkv', () => {
  class MockMMKV {
    constructor() {
      this.store = new Map();
    }
    set(k, v) {
      this.store.set(k, String(v));
    }
    getString(k) {
      return this.store.has(k) ? this.store.get(k) : undefined;
    }
    getBoolean(k) {
      return this.store.get(k) === 'true';
    }
    getNumber(k) {
      return this.store.has(k) ? Number(this.store.get(k)) : undefined;
    }
    contains(k) {
      return this.store.has(k);
    }
    remove(k) {
      return this.store.delete(k);
    }
    getAllKeys() {
      return Array.from(this.store.keys());
    }
    clearAll() {
      this.store.clear();
    }
  }
  return { createMMKV: () => new MockMMKV(), MMKV: MockMMKV };
});

// AsyncStorage (imported by the Firebase persistence wrapper) has no native
// module under Jest — use the official in-memory mock.
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

// In-memory mock for expo-secure-store (no native keychain in Jest).
jest.mock('expo-secure-store', () => {
  const store = new Map();
  return {
    getItemAsync: jest.fn((k) => Promise.resolve(store.has(k) ? store.get(k) : null)),
    setItemAsync: jest.fn((k, v) => {
      store.set(k, v);
      return Promise.resolve();
    }),
    deleteItemAsync: jest.fn((k) => {
      store.delete(k);
      return Promise.resolve();
    }),
  };
});

// Deterministic random bytes / uuid for expo-crypto.
jest.mock('expo-crypto', () => ({
  getRandomBytes: (n) => new Uint8Array(n).fill(7),
  randomUUID: () => '00000000-0000-4000-8000-000000000000',
  digestStringAsync: (_algo, value) => Promise.resolve(`hashed:${value}`),
  CryptoDigestAlgorithm: { SHA256: 'SHA-256' },
}));

// The native Firebase SDK (@react-native-firebase) has no native module under
// Jest, so mock its app + auth entry points. Unit tests drive these jest.fns
// directly (see firebaseAuthProvider.test.ts); no real native calls are made.
jest.mock('@react-native-firebase/app', () => ({
  getApp: jest.fn(() => ({ name: '[DEFAULT]' })),
  getApps: jest.fn(() => []),
  initializeApp: jest.fn(),
}));
jest.mock('@react-native-firebase/auth', () => ({
  getAuth: jest.fn(() => ({ currentUser: null })),
  signInWithPhoneNumber: jest.fn(),
  signInWithCredential: jest.fn(),
  signOut: jest.fn(() => Promise.resolve()),
  // Modular getIdTokenResult delegates to the fake user's own method so test
  // fixtures can shape the token result per case.
  getIdTokenResult: jest.fn((user, forceRefresh) => user.getIdTokenResult(forceRefresh)),
  GoogleAuthProvider: {
    credential: jest.fn((idToken, accessToken) => ({
      providerId: 'google.com',
      idToken,
      accessToken,
    })),
  },
  AppleAuthProvider: {
    credential: jest.fn((token, secret) => ({ providerId: 'apple.com', token, secret })),
  },
  PhoneAuthProvider: {
    credential: jest.fn((verificationId, verificationCode) => ({
      providerId: 'phone',
      verificationId,
      verificationCode,
    })),
  },
  OAuthProvider: class {
    credential() {
      return {};
    }
  },
}));

// Mock expo-localization so i18n init is deterministic.
jest.mock('expo-localization', () => ({
  getLocales: () => [{ languageCode: 'ta', languageTag: 'ta-IN' }],
}));

// react-native-reanimated@4.5.1's own `mock.ts` is not a safe drop-in under
// this jest-expo version: it re-exports real runtime code from its index (it
// only replaces the animation *API* with no-ops -- it still imports the real
// module graph for test utilities like `setUpTests`). That real index
// unconditionally calls `init()` on the real `react-native-worklets` package
// (node_modules/react-native-worklets/src/index.ts), which does genuine
// native-coupled work at import time: constructing a `NativeWorklets` native
// module handle and registering a "guard" worklet through the real
// serialization/cloning pipeline (node_modules/react-native-worklets/src/
// memory/serializable.native.ts). Two attempts at papering over this with
// global stubs each got further before hitting the next real subsystem
// underneath (native module handle -> serializable-ref cache -> WeakMap
// keyed on values only the real native side can produce) -- confirming this
// isn't a one-line gap but the whole native layer being unreachable under
// Jest, which jest-expo@57.0.3 has no accommodation for yet (worklets 0.10.x
// is newer than what this jest-expo release was built against).
//
// Rather than keep guessing at worklets' internal serialization contract,
// mock react-native-reanimated by hand with exactly the API surface this
// app actually uses (confirmed via `grep -rl "from 'react-native-reanimated'"
// components features app hooks`, 2026-08 pre-release audit: AgOfflineBanner,
// AgSkeleton, TypingIndicator, BoundaryEditor, HomeScreen -- and no test file
// imports reanimated's own test utilities, so nothing here needs to match
// the real package beyond these names). Every value below resolves
// synchronously instead of animating, matching how reanimated's classic
// (pre-v4) mock behaved before its own mock started requiring real internals.
jest.mock('react-native-reanimated', () => {
  const ReactLocal = require('react');
  const { View } = require('react-native');

  // Animated.View: a plain View that drops reanimated-only props (entering/
  // exiting/layout/sharedTransitionTag) instead of forwarding them to the
  // native View, which would otherwise log "unknown prop" warnings.
  const AnimatedView = ReactLocal.forwardRef(function AnimatedView(
    { entering, exiting, layout, sharedTransitionTag, ...rest },
    ref,
  ) {
    return ReactLocal.createElement(View, { ...rest, ref });
  });

  // Layout-animation builders (FadeInUp/FadeOutUp/FadeInDown/...): only
  // `.duration()`/`.delay()` chaining is used in this app, and Animated.View
  // above ignores the `entering`/`exiting` prop entirely, so the builder just
  // needs to stay chainable without throwing.
  const makeAnimationBuilder = () => {
    const builder = {
      duration: () => builder,
      delay: () => builder,
      springify: () => builder,
      damping: () => builder,
      easing: () => builder,
    };
    return builder;
  };

  return {
    __esModule: true,
    // `default.createAnimatedComponent` is called unconditionally at *import
    // time* by react-native-gesture-handler's own Wrap.tsx (`Reanimated?.
    // default?.createAnimatedComponent(Wrap)`, node_modules/
    // react-native-gesture-handler/src/handlers/gestures/GestureDetector/
    // Wrap.tsx:35) whenever anything imports gesture-handler -- which
    // BoundaryEditor.tsx does. Modeled on reanimated's own (safe, pure)
    // `default.createAnimatedComponent: ID` from src/mock.ts: since nothing
    // under test actually inspects the wrapped component's animated
    // behavior, returning the component unchanged is sufficient.
    default: { View: AnimatedView, createAnimatedComponent: (Component) => Component },
    FadeIn: makeAnimationBuilder(),
    FadeOut: makeAnimationBuilder(),
    FadeInUp: makeAnimationBuilder(),
    FadeOutUp: makeAnimationBuilder(),
    FadeInDown: makeAnimationBuilder(),
    FadeOutDown: makeAnimationBuilder(),
    useSharedValue: (initial) => ({ value: initial }),
    useAnimatedStyle: (fn) => fn(),
    withTiming: (toValue, _config, callback) => {
      callback?.(true);
      return toValue;
    },
    withSpring: (toValue, _config, callback) => {
      callback?.(true);
      return toValue;
    },
    withDelay: (_delay, animation) => animation,
    withRepeat: (animation) => animation,
    withSequence: (...animations) => animations.at(-1),
    runOnJS: (fn) => fn,
    runOnUI: (fn) => fn,
    cancelAnimation: () => {},
    // `useEvent` is called by gesture-handler's useAnimatedGesture hook
    // (node_modules/react-native-gesture-handler/src/handlers/gestures/
    // GestureDetector/useAnimatedGesture.ts:201) whenever a GestureDetector
    // with a reanimated-backed gesture actually renders. Modeled on
    // reanimated's own mock.ts `useEvent: () => NOOP` -- no test in this
    // suite simulates real native gesture events, so a no-op handler is
    // sufficient.
    useEvent: () => () => {},
  };
});
process.env.EXPO_PUBLIC_DEV_OTP = '123456';
