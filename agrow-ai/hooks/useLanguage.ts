import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { setLanguage as persistLanguage } from '@/localization';
import type { SupportedLanguage } from '@/types';

/** Current UI language plus a setter that persists the choice. */
export function useLanguage() {
  const { i18n } = useTranslation();
  const language = (i18n.language as SupportedLanguage) ?? 'ta';

  const setLanguage = useCallback(
    (lng: SupportedLanguage) => persistLanguage(lng),
    [],
  );

  const isTamil = language === 'ta';

  return { language, setLanguage, isTamil };
}
