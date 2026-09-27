import type { OrganicFarmMode } from './types';
import { useOrganicProfile } from './hooks/useOrganic';

/**
 * How chemical options are shown, driven by the farm's organic mode:
 * - show:        conventional (or no profile) -- organic first, then chemical
 * - last_resort: organic preferred -- chemical shown with "only if organic fails"
 * - hide:        transitioning / fully organic -- chemicals would break conversion
 */
export type ChemicalPolicy = 'show' | 'last_resort' | 'hide';

export function chemicalPolicyForMode(mode: OrganicFarmMode | null | undefined): ChemicalPolicy {
  if (mode === 'transitioning' || mode === 'fully_organic') return 'hide';
  if (mode === 'organic_preferred') return 'last_resort';
  return 'show';
}

/** Chemical policy for a farm (defaults to "show" while loading or with no profile). */
export function useChemicalPolicy(farmId: string | null | undefined): ChemicalPolicy {
  const profile = useOrganicProfile(farmId ?? '');
  return chemicalPolicyForMode(profile.data?.mode);
}

/** Chemical items to display for a policy: hidden, flagged, or unchanged. */
export function applyChemicalPolicy(
  items: string[],
  policy: ChemicalPolicy,
  t: (key: string) => string,
): string[] {
  if (items.length === 0) return items;
  if (policy === 'hide') return [t('organic.chemicalNotAllowed')];
  if (policy === 'last_resort') return [...items, t('organic.chemicalLastResort')];
  return items;
}
