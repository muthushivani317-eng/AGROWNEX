/** AI Chat constants. */

export const AI_STORE_KEY = 'agrowai.ai.conversations';
export const MAX_MESSAGE_CHARS = 2000;

export const aiKeys = {
  all: ['ai'] as const,
  history: ['ai', 'history'] as const,
  conversation: (id: string) => ['ai', 'conversation', id] as const,
};

/** Starter prompts shown on an empty chat (localized via i18n keys). */
export const SUGGESTION_KEYS = [
  'ai.suggestion1',
  'ai.suggestion2',
  'ai.suggestion3',
  'ai.suggestion4',
] as const;
