/** Display model identifiers as readable labels without changing their meaning. */
export function formatDiagnosisName(value: string | null): string | null {
  if (!value) return null;
  const diagnosis = value.includes('__') ? value.split('__').at(-1)! : value;
  const label = diagnosis.split(/[_-]+/).filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ').trim();
  return label || null;
}
