/** Organic is enabled by default; an explicit release flag can fail it closed. */
export function resolveOrganicFeatureEnabled(value: string | undefined): boolean { return value !== 'false'; }
export const organicFeatureEnabled = resolveOrganicFeatureEnabled(process.env.EXPO_PUBLIC_AGROWAI_ORGANIC_ENABLED);
