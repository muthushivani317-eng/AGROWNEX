import { uuid } from '@/utils/id';

import { DEFAULT_PAGE_SIZE, HISTORY_DAYS } from '../constants';
import type {
  AddFavouriteInput,
  CommodityCategory,
  MarketFavourite,
  MarketFilters,
  MarketHistory,
  MarketPrice,
  MarketPricePage,
  MarketSearchResult,
} from '../types';
import { marketStorage } from './marketStorage';
import { MarketError, type MarketProvider } from './marketProvider';

/**
 * Local, offline market provider. Serves the same deterministic sample prices as
 * the backend mock so the screen is fully usable in dev / without a backend, and
 * persists favourites in MMKV. Never fabricates prices for production — it is only
 * selected when no verified backend is configured (docs/PRODUCT_RULES.md).
 */
interface SampleRow {
  commodity: string;
  variety: string;
  category: CommodityCategory;
  market: string;
  district: string;
  state: string;
  min: number;
  max: number;
  modal: number;
}

const SAMPLE: SampleRow[] = [
  { commodity: 'Paddy', variety: 'Common', category: 'cereal', market: 'Thanjavur', district: 'Thanjavur', state: 'Tamil Nadu', min: 1980, max: 2120, modal: 2050 },
  { commodity: 'Rice', variety: 'Fine', category: 'cereal', market: 'Chennai', district: 'Chennai', state: 'Tamil Nadu', min: 3500, max: 3900, modal: 3700 },
  { commodity: 'Tomato', variety: 'Local', category: 'vegetable', market: 'Coimbatore', district: 'Coimbatore', state: 'Tamil Nadu', min: 1200, max: 1800, modal: 1500 },
  { commodity: 'Onion', variety: 'Big', category: 'vegetable', market: 'Madurai', district: 'Madurai', state: 'Tamil Nadu', min: 1500, max: 2200, modal: 1850 },
  { commodity: 'Groundnut', variety: 'Bold', category: 'oilseed', market: 'Salem', district: 'Salem', state: 'Tamil Nadu', min: 5800, max: 6400, modal: 6100 },
  { commodity: 'Sugarcane', variety: 'Local', category: 'cash_crop', market: 'Erode', district: 'Erode', state: 'Tamil Nadu', min: 300, max: 360, modal: 330 },
  { commodity: 'Cotton', variety: 'Medium', category: 'cash_crop', market: 'Coimbatore', district: 'Coimbatore', state: 'Tamil Nadu', min: 6800, max: 7400, modal: 7100 },
  { commodity: 'Banana', variety: 'Nendran', category: 'fruit', market: 'Trichy', district: 'Tiruchirappalli', state: 'Tamil Nadu', min: 2400, max: 3000, modal: 2700 },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function matches(value: string, needle?: string | null): boolean {
  return !needle || value.toLowerCase().includes(needle.trim().toLowerCase());
}

function toPrice(row: SampleRow): MarketPrice {
  const now = new Date().toISOString();
  return {
    id: `local-${row.commodity}-${row.market}`.toLowerCase(),
    commodity: row.commodity,
    variety: row.variety,
    category: row.category,
    market: row.market,
    district: row.district,
    state: row.state,
    minimumPrice: row.min,
    maximumPrice: row.max,
    modalPrice: row.modal,
    unit: 'quintal',
    priceDate: today(),
    source: 'mock',
    verified: true,
    isStale: false,
    ageDays: 0,
    updatedAt: now,
  };
}

function filterRows(filters: MarketFilters): SampleRow[] {
  return SAMPLE.filter(
    (row) =>
      matches(row.commodity, filters.crop) &&
      matches(row.market, filters.market) &&
      matches(row.district, filters.district) &&
      matches(row.state, filters.state),
  );
}

export const localMarketProvider: MarketProvider = {
  async prices(filters: MarketFilters): Promise<MarketPricePage> {
    const rows = filterRows(filters);
    const pageSize = filters.pageSize ?? DEFAULT_PAGE_SIZE;
    const page = filters.page ?? 1;
    const items = rows.slice((page - 1) * pageSize, page * pageSize).map(toPrice);
    return {
      items,
      page,
      pageSize,
      total: rows.length,
      totalPages: Math.max(1, Math.ceil(rows.length / pageSize)),
    };
  },

  async history(crop: string, market: string): Promise<MarketHistory> {
    const row = SAMPLE.find(
      (r) =>
        matches(r.commodity, crop) && matches(r.market, market),
    );
    if (!row) throw new MarketError('market_data_unavailable', 'No history available.');
    const points = Array.from({ length: HISTORY_DAYS }).map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (HISTORY_DAYS - 1 - i));
      const drift = Math.round(Math.sin(i / 4) * 60);
      return {
        recordedDate: d.toISOString().slice(0, 10),
        minimumPrice: row.min + drift,
        maximumPrice: row.max + drift,
        modalPrice: row.modal + drift,
        unit: 'quintal' as const,
      };
    });
    return {
      commodity: row.commodity,
      variety: row.variety,
      market: row.market,
      district: row.district,
      state: row.state,
      unit: 'quintal',
      points,
    };
  },

  async search(term: string): Promise<MarketSearchResult[]> {
    const t = term.trim().toLowerCase();
    if (!t) return [];
    const results: MarketSearchResult[] = [];
    const seen = new Set<string>();
    const push = (type: MarketSearchResult['type'], value: string) => {
      const key = `${type}:${value.toLowerCase()}`;
      if (value.toLowerCase().includes(t) && !seen.has(key)) {
        seen.add(key);
        results.push({ type, value, label: value });
      }
    };
    for (const row of SAMPLE) {
      push('crop', row.commodity);
      push('market', row.market);
      push('district', row.district);
      push('state', row.state);
    }
    return results;
  },

  async favourites(): Promise<MarketFavourite[]> {
    return marketStorage.favourites();
  },

  async addFavourite(input: AddFavouriteInput): Promise<MarketFavourite> {
    const existing = marketStorage
      .favourites()
      .find(
        (f) =>
          f.commodity === input.commodity &&
          f.market === input.market &&
          f.district === input.district,
      );
    if (existing) throw new MarketError('market_favourite_exists', 'Already saved.');
    const row = SAMPLE.find(
      (r) => r.commodity === input.commodity && r.market === input.market,
    );
    const favourite: MarketFavourite = {
      id: uuid(),
      commodity: input.commodity,
      market: input.market,
      district: input.district,
      state: input.state,
      createdAt: new Date().toISOString(),
      latest: row ? toPrice(row) : null,
    };
    marketStorage.addFavourite(favourite);
    return favourite;
  },

  async removeFavourite(id: string): Promise<void> {
    marketStorage.removeFavourite(id);
  },
};
