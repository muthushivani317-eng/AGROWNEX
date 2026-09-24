/**
 * Generalizes the per-hectare quantity calculation that
 * `backend/app/modules/organic/plan_engine.py::build_soil_plan` already does
 * for soil-amendment inputs (compost/farmyard_manure/vermicompost/green_manure)
 * to ANY approved input with a `guidance.application_rate` of that same shape
 * ({ value, unit }, unit "kg/ha" | "tonne/ha" -- the only rate shape the
 * backend itself ever produces or validates). No other guidance shape
 * (dilution ratios, per-plant dosage, timing/frequency) exists anywhere in
 * the backend today, so this deliberately does NOT attempt to compute
 * anything for those -- inventing a conversion for units the backend never
 * emits would be a guess, not a calculation.
 */

const HECTARE_RATE_UNITS = new Set(['kg/ha', 'tonne/ha']);

export interface CalculatedInputQuantity {
  rateValue: number;
  rateUnit: string;
  quantity: number;
  unit: string;
}

export function calculateInputQuantity(
  guidance: Record<string, unknown>,
  areaHectares: number | null,
): CalculatedInputQuantity | null {
  if (!areaHectares || areaHectares <= 0) return null;
  const rate = guidance?.application_rate;
  if (!rate || typeof rate !== 'object') return null;
  const { value, unit } = rate as { value?: unknown; unit?: unknown };
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) return null;
  if (typeof unit !== 'string' || !HECTARE_RATE_UNITS.has(unit)) return null;
  return {
    rateValue: value,
    rateUnit: unit,
    quantity: Math.round(value * areaHectares * 1000) / 1000,
    unit: unit.replace('/ha', ''),
  };
}

/**
 * `OrganicInput.category` is a free-text admin-authored column in the
 * backend (no enum) -- so this only recognizes the exact categories
 * `plan_engine.py::build_soil_plan` itself already treats as soil
 * amendments, and falls back to the existing generic 'custom' practice
 * type otherwise, rather than guessing a mapping for categories the
 * backend has no fixed list of.
 */
const AMENDMENT_CATEGORIES = new Set([
  'compost',
  'farmyard_manure',
  'vermicompost',
  'green_manure',
]);

export function practiceTypeForCategory(category: string): 'amendment' | 'custom' {
  return AMENDMENT_CATEGORIES.has(category) ? 'amendment' : 'custom';
}
