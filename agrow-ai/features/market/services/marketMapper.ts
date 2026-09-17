import type {
  ApiMarketFavourite,
  ApiMarketHistory,
  ApiMarketPrice,
  ApiMarketPricePage,
  ApiMarketSearchResult,
  MarketFavourite,
  MarketHistory,
  MarketPrice,
  MarketPricePage,
  MarketSearchResult,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToPrice(dto: ApiMarketPrice): MarketPrice {
  return {
    id: dto.id,
    commodity: dto.commodity,
    variety: dto.variety,
    category: dto.category,
    market: dto.market,
    district: dto.district,
    state: dto.state,
    minimumPrice: dto.minimum_price,
    maximumPrice: dto.maximum_price,
    modalPrice: dto.modal_price,
    unit: dto.unit,
    priceDate: dto.price_date,
    source: dto.source,
    verified: dto.verified,
    isStale: dto.is_stale,
    ageDays: dto.age_days,
    updatedAt: dto.updated_at,
  };
}

export function apiToPage(dto: ApiMarketPricePage): MarketPricePage {
  return {
    items: dto.items.map(apiToPrice),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}

export function apiToHistory(dto: ApiMarketHistory): MarketHistory {
  return {
    commodity: dto.commodity,
    variety: dto.variety,
    market: dto.market,
    district: dto.district,
    state: dto.state,
    unit: dto.unit,
    points: dto.points.map((p) => ({
      recordedDate: p.recorded_date,
      minimumPrice: p.minimum_price,
      maximumPrice: p.maximum_price,
      modalPrice: p.modal_price,
      unit: p.unit,
    })),
  };
}

export function apiToSearchResult(dto: ApiMarketSearchResult): MarketSearchResult {
  return { type: dto.type, value: dto.value, label: dto.label };
}

export function apiToFavourite(dto: ApiMarketFavourite): MarketFavourite {
  return {
    id: dto.id,
    commodity: dto.commodity,
    market: dto.market,
    district: dto.district,
    state: dto.state,
    createdAt: dto.created_at,
    latest: dto.latest ? apiToPrice(dto.latest) : null,
  };
}
