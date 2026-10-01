import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { createMMKV, type MMKV } from 'react-native-mmkv';
import type { StateStorage } from 'zustand/middleware';

import { logger } from './logger';

/**
 * Storage layer (docs/FRONTEND_ARCHITECTURE.md → MMKV).
 *
 * Two instances:
 *  - `appMMKV`     : fast, synchronous, non-sensitive app state & cache.
 *  - `secureMMKV`  : AES-256 encrypted store for tokens & sensitive data. The key
 *                    is generated once and kept in the OS keychain via
 *                    SecureStore, so the encrypted DB is useless without it.
 */
export const appMMKV: MMKV = createMMKV({ id: 'agrowai.app' });

const MMKV_KEY_ALIAS = 'agrowai.mmkv.key';
let secureMMKV: MMKV | null = null;

async function loadOrCreateEncryptionKey(): Promise<string> {
  const existing = await SecureStore.getItemAsync(MMKV_KEY_ALIAS);
  if (existing) return existing;
  // 16 random bytes → 32 hex chars (32-byte string) for AES-256.
  const bytes = Crypto.getRandomBytes(16);
  const key = Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  await SecureStore.setItemAsync(MMKV_KEY_ALIAS, key);
  return key;
}

/**
 * Initialise the encrypted store. Must be awaited once during app bootstrap
 * (before reading/writing sensitive values). Idempotent.
 */
export async function initSecureStorage(): Promise<void> {
  if (secureMMKV) return;

  // SecureStore is backed by the native OS keychain and has no web
  // implementation. Keep web startup functional using MMKV's browser-backed
  // storage. Production web authentication should use HttpOnly cookies when
  // the website begins handling authenticated sessions.
  if (Platform.OS === 'web') {
    secureMMKV = createMMKV({ id: 'agrowai.secure.web' });
    return;
  }

  try {
    const key = await loadOrCreateEncryptionKey();
    secureMMKV = createMMKV({
      id: 'agrowai.secure',
      encryptionKey: key,
      encryptionType: 'AES-256',
    });
  } catch (e) {
    logger.error('storage.initSecure', e);
    // Fail closed: never write tokens to an unencrypted file. Keep them in
    // memory for this session only (the farmer signs in again next launch).
    secureMMKV = createMemoryStore();
  }
}

/** Session-only store used when the OS keystore is unavailable. */
function createMemoryStore(): MMKV {
  const values = new Map<string, string>();
  const store = {
    getString: (key: string) => values.get(key),
    set: (key: string, value: string | number | boolean) => {
      values.set(key, String(value));
    },
    remove: (key: string) => values.delete(key),
    contains: (key: string) => values.has(key),
    clearAll: () => values.clear(),
    getAllKeys: () => Array.from(values.keys()),
  };
  return store as unknown as MMKV;
}

function requireSecure(): MMKV {
  if (!secureMMKV) {
    throw new Error('Secure storage not initialised — call initSecureStorage() first.');
  }
  return secureMMKV;
}

function readJSON<T>(instance: MMKV, key: string): T | null {
  const raw = instance.getString(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/** Non-sensitive key/value helpers over the app instance (synchronous). */
export const appStorage = {
  getString: (k: string) => appMMKV.getString(k) ?? null,
  set: (k: string, v: string) => appMMKV.set(k, v),
  remove: (k: string) => appMMKV.remove(k),
  getJSON: <T>(k: string) => readJSON<T>(appMMKV, k),
  setJSON: (k: string, v: unknown) => appMMKV.set(k, JSON.stringify(v)),
};

/** Sensitive key/value helpers over the encrypted instance. */
export const secureStorage = {
  getString: (k: string) => requireSecure().getString(k) ?? null,
  set: (k: string, v: string) => requireSecure().set(k, v),
  remove: (k: string) => requireSecure().remove(k),
  getJSON: <T>(k: string) => readJSON<T>(requireSecure(), k),
  setJSON: (k: string, v: unknown) => requireSecure().set(k, JSON.stringify(v)),
};

/** zustand `persist` adapter backed by the app (non-sensitive) MMKV instance. */
export const mmkvZustandStorage: StateStorage = {
  getItem: (name) => appMMKV.getString(name) ?? null,
  setItem: (name, value) => appMMKV.set(name, value),
  removeItem: (name) => appMMKV.remove(name),
};

export const StorageKeys = {
  authTokens: 'agrowai.auth.tokens',
  authUser: 'agrowai.auth.user',
  lastActiveAt: 'agrowai.auth.lastActiveAt',
  themePref: 'agrowai.pref.theme',
  languagePref: 'agrowai.pref.language',
  languageSelected: 'agrowai.flag.languageSelected',
  onboarded: 'agrowai.flag.onboarded',
} as const;
