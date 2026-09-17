export function resolveHarvestCycleId(
  farmId: string,
  sowingDate: string | null | undefined,
  growthSessionId: string | null | undefined,
): string | null {
  if (growthSessionId) return growthSessionId;
  if (!sowingDate) return null;
  return `farm-${farmId}-${sowingDate}`;
}
