import type { ProcurementAnalytics, ProcurementBucket } from '../types';

/**
 * Pure client mirror of the backend Admin Engine's procurement analytics
 * (village/crop/season splits + a monthly quantity trend). Kept faithful to
 * `app/modules/admin/engine.py` so the local (no-backend / dev) provider computes the
 * same figures. Nothing is fabricated — an unconvertible unit contributes 0 kg, and a
 * missing harvest date is excluded from the dated trend.
 */

export interface ProcurementFact {
  village: string | null;
  crop: string | null;
  harvestDate: string | null; // ISO date/datetime
  quantity: number;
  unit: string;
}

/** kg per unit (bag is not convertible → null, as on the backend). */
export function toKilograms(quantity: number, unit: string): number | null {
  const u = unit.trim().toLowerCase();
  if (u === 'kg' || u === 'kilogram' || u === 'kilograms') return quantity;
  if (u === 'quintal' || u === 'quintals') return quantity * 100;
  if (u === 'tonne' || u === 'ton' || u === 'tonnes') return quantity * 1000;
  return null;
}

function kg(quantity: number, unit: string): number {
  return toKilograms(quantity, unit) ?? 0;
}

/** Tamil Nadu season for a 1-based month (mirror of memory.season_for_month). */
export function seasonForMonth(month: number): string {
  if (month >= 6 && month <= 10) return 'kharif';
  if (month === 11 || month === 12 || month === 1 || month === 2) return 'rabi';
  if (month >= 3 && month <= 5) return 'summer';
  return 'unknown';
}

function bucketBy(
  facts: ProcurementFact[],
  keyFn: (f: ProcurementFact) => string | null,
): ProcurementBucket[] {
  const counts = new Map<string, number>();
  const kilos = new Map<string, number>();
  for (const f of facts) {
    const key = keyFn(f) ?? 'unknown';
    counts.set(key, (counts.get(key) ?? 0) + 1);
    kilos.set(key, (kilos.get(key) ?? 0) + kg(f.quantity, f.unit));
  }
  const rows: ProcurementBucket[] = [...counts.keys()].map((label) => ({
    label,
    count: counts.get(label) ?? 0,
    quantityKg: Math.round((kilos.get(label) ?? 0) * 100) / 100,
  }));
  rows.sort((a, b) => b.count - a.count || b.quantityKg - a.quantityKg);
  return rows;
}

function monthKey(iso: string): string {
  const d = new Date(iso);
  const m = `${d.getUTCMonth() + 1}`.padStart(2, '0');
  return `${d.getUTCFullYear()}-${m}`;
}

export function computeProcurementAnalytics(facts: ProcurementFact[]): ProcurementAnalytics {
  const byVillage = bucketBy(facts, (f) => f.village);
  const byCrop = bucketBy(facts, (f) => f.crop);
  const bySeason = bucketBy(facts, (f) =>
    f.harvestDate ? seasonForMonth(new Date(f.harvestDate).getUTCMonth() + 1) : null,
  );

  const trendKg = new Map<string, number>();
  const trendCount = new Map<string, number>();
  for (const f of facts) {
    if (!f.harvestDate) continue;
    const label = monthKey(f.harvestDate);
    trendKg.set(label, (trendKg.get(label) ?? 0) + kg(f.quantity, f.unit));
    trendCount.set(label, (trendCount.get(label) ?? 0) + 1);
  }
  const quantityTrend = [...trendKg.keys()]
    .sort()
    .map((label) => ({
      label,
      quantityKg: Math.round((trendKg.get(label) ?? 0) * 100) / 100,
      count: trendCount.get(label) ?? 0,
    }));

  const totalKg = facts.reduce((sum, f) => sum + kg(f.quantity, f.unit), 0);

  return {
    byVillage,
    byCrop,
    bySeason,
    quantityTrend,
    totalOffers: facts.length,
    totalQuantityKg: Math.round(totalKg * 100) / 100,
  };
}
