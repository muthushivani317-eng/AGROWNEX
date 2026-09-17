import type { BuildProfile } from "./env";

/** Local feature samples are a developer tool, never a field/release fallback. */
export function mayUseLocalFeatureMocks(
  profile: BuildProfile,
  backendConfigured: boolean,
): boolean {
  if (backendConfigured) return false;
  return profile === "development" || profile === "localStandalone";
}
