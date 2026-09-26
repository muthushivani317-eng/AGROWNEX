/** Turns backend action codes (e.g. `organic_input.neem_oil`) into readable, translated titles. */
type Translate = (key: string, options?: Record<string, unknown>) => string;

export const humanizeCode = (value: string): string => {
  const text = value.replace(/[._-]+/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : value;
};

export function organicActionTitle(code: string, t: Translate): string {
  if (code.startsWith('organic_input.')) {
    return t('organic.actionCode.applyInput', { name: humanizeCode(code.slice('organic_input.'.length)) });
  }
  if (code.startsWith('field_scouting_')) {
    return t('organic.actionCode.fieldScouting', { area: humanizeCode(code.slice('field_scouting_'.length)) });
  }
  const key = code.startsWith('organic.disease.') ? code.slice('organic.disease.'.length) : code;
  return t(`organic.actionCode.${key}`, { defaultValue: humanizeCode(key) });
}
