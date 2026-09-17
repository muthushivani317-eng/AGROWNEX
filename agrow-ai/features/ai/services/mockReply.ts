import i18n, { resources } from '@/localization';
import type { SupportedLanguage } from '@/types';

/** Deterministic, translated offline reply generator for development. */
const TITLE_MAX = 60;

function translate(key: 'mockTitle' | 'mockReplyEn' | 'mockReplyTa', language: SupportedLanguage, question?: string): string {
  const translated = i18n.t?.(`ai.${key}`, { lng: language, question });
  if (translated) return translated;
  const template = resources[language].translation.ai[key] as string;
  return question ? template.replace('{{question}}', question) : template;
}

export function deriveTitle(message: string, language: SupportedLanguage = 'en'): string {
  const single = message.trim().replace(/\s+/g, ' ');
  return single.slice(0, TITLE_MAX) || translate('mockTitle', language);
}

export function generateMockReply(message: string, language: SupportedLanguage): string {
  const question = message.trim().slice(0, 120);
  return translate(language === 'ta' ? 'mockReplyTa' : 'mockReplyEn', language, question);
}
