/** Convert backend sampling reason codes into concise, user-facing text.
 *
 * Example:
 *   spatial_variability:higher_vigor_or_moisture
 *   -> Higher vigor or moisture
 */
export function formatSamplingReason(reason: string): string {
  const specificReason = reason.split(":").at(-1)?.trim() ?? "";
  const words = specificReason.replace(/[_-]+/g, " ").replace(/\s+/g, " ");

  if (!words) return "Sampling priority area";
  return words[0].toUpperCase() + words.slice(1).toLowerCase();
}
