/**
 * Market Prices domain types (docs/API_CONTRACT.md → MARKET).
 * Client-side camelCase mirror of the backend market schemas. Prices come only
 * from verified sources (docs/PRODUCT_RULES.md) — nothing here is fabricated.
 */

export type CommodityCategory =
  | 'cereal'
  | 'pulse'
  | 'oilseed'
  | 'vegetable'
  | 'fruit'
  | 'spice'
  | 'cash_crop'
  | 'other';

export type PriceUnit = 'quintal' | 'kg' | 'tonne';

export type MarketSearchType = 'crop' | 'market' | 'district' | 'state';

export type MarketView = 'all' | 'today' | 'nearby' | 'favourites';

export interface MarketPrice {
  id: string;
  commodity: string;
  variety: string;
  category: CommodityCategory;
  market: string;
  district: string;
  state: string;
  minimumPrice: number;
  maximumPrice: number;
  modalPrice: number;
  unit: PriceUnit;
  priceDate: string; // YYYY-MM-DD
  source: string;
  verified: boolean;
  isStale: boolean;
  ageDays: number;
  updatedAt: string;
}

export interface MarketFilters {
  crop?: string | null;
  market?: string | null;
  district?: string | null;
  state?: string | null;
  page?: number;
  pageSize?: number;
  todayOnly?: boolean;
}

export interface MarketPricePage {
  fromCache?: boolean;
  items: MarketPrice[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface MarketHistoryPoint {
  recordedDate: string;
  minimumPrice: number;
  maximumPrice: number;
  modalPrice: number;
  unit: PriceUnit;
}

export interface MarketHistory {
  commodity: string;
  variety: string;
  market: string;
  district: string;
  state: string;
  unit: PriceUnit;
  points: MarketHistoryPoint[];
}

export interface MarketSearchResult {
  type: MarketSearchType;
  value: string;
  label: string;
}

export interface MarketFavourite {
  id: string;
  commodity: string;
  market: string;
  district: string;
  state: string;
  createdAt: string;
  latest: MarketPrice | null;
}

export interface AddFavouriteInput {
  commodity: string;
  market: string;
  district: string;
  state: string;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiMarketPrice {
  id: string;
  commodity: string;
  variety: string;
  category: CommodityCategory;
  market: string;
  district: string;
  state: string;
  minimum_price: number;
  maximum_price: number;
  modal_price: number;
  unit: PriceUnit;
  price_date: string;
  source: string;
  verified: boolean;
  is_stale: boolean;
  age_days: number;
  updated_at: string;
}

export interface ApiMarketPricePage {
  items: ApiMarketPrice[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ApiMarketHistoryPoint {
  recorded_date: string;
  minimum_price: number;
  maximum_price: number;
  modal_price: number;
  unit: PriceUnit;
}

export interface ApiMarketHistory {
  commodity: string;
  variety: string;
  market: string;
  district: string;
  state: string;
  unit: PriceUnit;
  points: ApiMarketHistoryPoint[];
}

export interface ApiMarketSearchResult {
  type: MarketSearchType;
  value: string;
  label: string;
}

export interface ApiMarketFavourite {
  id: string;
  commodity: string;
  market: string;
  district: string;
  state: string;
  created_at: string;
  latest: ApiMarketPrice | null;
}
