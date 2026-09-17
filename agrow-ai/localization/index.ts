import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import { appStorage, StorageKeys } from '@/lib/storage';
import type { SupportedLanguage } from '@/types';

import { en } from './locales/en';
import { ta } from './locales/ta';

export const resources = {
  en: { translation: en },
  ta: { translation: ta },
} as const;

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = ['ta', 'en'];
export const DEFAULT_LANGUAGE: SupportedLanguage = 'ta';

/**
 * Initialise i18next. Reads a previously saved preference; otherwise starts in
 * Tamil. Must be awaited before the UI renders text.
 */
export async function initI18n(): Promise<typeof i18n> {
  const saved = appStorage.getString(
    StorageKeys.languagePref,
  ) as SupportedLanguage | null;
  const lng =
    saved && SUPPORTED_LANGUAGES.includes(saved) ? saved : DEFAULT_LANGUAGE;

  if (!i18n.isInitialized) {
    await i18n.use(initReactI18next).init({
      resources,
      lng,
      fallbackLng: 'en',
      defaultNS: 'translation',
      interpolation: { escapeValue: false },
      returnNull: false,
      returnEmptyString: false,
      // i18next calls parseMissingKeyHandler for EVERY missing key,
      // regardless of whether the call site passed a `defaultValue` -- and
      // whatever this handler returns replaces the key's resolved value
      // entirely, including that defaultValue. This used to unconditionally
      // return the literal string "Content unavailable", which meant any
      // `t('some.missing.key', { defaultValue: 'Real fallback text' })`
      // call anywhere in the app silently discarded its own coded-in
      // fallback and showed "Content unavailable" instead (found live
      // 2026-08-17 on GeneralDiagnosisScreen: several call sites had good
      // English defaultValue text that never reached the screen because of
      // this). Now: honour a real defaultValue when the call site provided
      // one, and only fall back to the generic message for keys with no
      // defaultValue at all -- so a genuinely-missing translation still
      // never shows a raw i18n key dot-path to a farmer.
      parseMissingKeyHandler: (_key: string, defaultValue?: string) =>
        typeof defaultValue === 'string' && defaultValue.length > 0
          ? defaultValue
          : 'Content unavailable',
      compatibilityJSON: 'v4',
    });
  } else {
    await i18n.changeLanguage(lng);
  }
  return i18n;
}

export function setLanguage(lng: SupportedLanguage): Promise<unknown> {
  appStorage.set(StorageKeys.languagePref, lng);
  return i18n.changeLanguage(lng);
}

export function getLanguage(): SupportedLanguage {
  return (i18n.language as SupportedLanguage) ?? DEFAULT_LANGUAGE;
}

export default i18n;
