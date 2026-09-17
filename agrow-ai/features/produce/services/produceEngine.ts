/**
 * Local procurement engine — a faithful, deterministic mirror of the backend
 * ``app/modules/produce/engine.py``. Used by the offline / local provider so the
 * app produces the same procurement intelligence without a backend. Pure: no I/O,
 * no side effects. Never fabricates a market price (value needs a verified
 * reference) or a buyer.
 */
import type {
  HarvestWindow,
  PriceReference,
  ProcurementInsight,
  ProduceUnit,
} from '../types';

const WINDOW_WEEK_DAYS = 7;
const WINDOW_MONTH_DAYS = 30;

/** Kilograms per unit for the convertible units (bag is intentionally absent). */
const UNIT_KG: Partial<Record<ProduceUnit, number>> = {
  kg: 1,
  quintal: 100,
  tonne: 1000,
};

export function daysBetween(target: string, today: Date): number {
  const start = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const end = new Date(target);
  return Math.round((start(end) - start(today)) / 86_400_000);
}

export function classifyWindow(daysToHarvest: number): HarvestWindow {
  if (daysToHarvest < 0) return 'overdue';
  if (daysToHarvest <= WINDOW_WEEK_DAYS) return 'this_week';
  if (daysToHarvest <= WINDOW_MONTH_DAYS) return 'this_month';
  return 'later';
}

export function toKilograms(quantity: number, unit: ProduceUnit): number | null {
  const factor = UNIT_KG[unit];
  return factor === undefined ? null : quantity * factor;
}

function valueFromPrice(
  quantityKg: number | null,
  pricePerUnit: number,
  unit: string,
): number | null {
  const unitKg = UNIT_KG[unit as ProduceUnit];
  if (quantityKg === null || unitKg === undefined || unitKg <= 0) return null;
  return Math.round((quantityKg / unitKg) * pricePerUnit * 100) / 100;
}

export interface OfferFacts {
  quantity: number;
  unit: ProduceUnit;
  expectedHarvestDate: string;
  askingPrice?: number | null;
}

export function computeInsight(
  offer: OfferFacts,
  price: PriceReference | null,
  today = new Date(),
): ProcurementInsight {
  const days = daysBetween(offer.expectedHarvestDate, today);
  const quantityKg = toKilograms(offer.quantity, offer.unit);
  const estimatedMarketValue =
    price !== null ? valueFromPrice(quantityKg, price.modalPrice, price.unit) : null;
  const estimatedAskingValue =
    offer.askingPrice != null
      ? Math.round(offer.quantity * offer.askingPrice * 100) / 100
      : null;

  return {
    daysToHarvest: days,
    harvestWindow: classifyWindow(days),
    quantityKg,
    estimatedMarketValue,
    estimatedAskingValue,
    priceReference: price,
  };
}
