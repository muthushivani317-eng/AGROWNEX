import type {
  CommodityCategory,
  MarketSearchType,
  MarketView,
  PriceUnit,
} from './types';

export const MARKET_PRICES_CACHE_KEY = 'agrowai.market.prices';
export const MARKET_FAVOURITES_KEY = 'agrowai.market.favourites';

export const DEFAULT_PAGE_SIZE = 20;
export const HISTORY_DAYS = 30;
export const SEARCH_DEBOUNCE_MS = 300;

export const marketKeys = {
  all: ['market'] as const,
  prices: (filterKey: string) => ['market', 'prices', filterKey] as const,
  history: (crop: string, market: string) =>
    ['market', 'history', crop, market] as const,
  search: (term: string) => ['market', 'search', term] as const,
  favourites: ['market', 'favourites'] as const,
};

export const MARKET_VIEWS: MarketView[] = ['all', 'today', 'nearby', 'favourites'];

export const VIEW_LABEL_KEY: Record<MarketView, string> = {
  all: 'market.viewAll',
  today: 'market.viewToday',
  nearby: 'market.viewNearby',
  favourites: 'market.viewFavourites',
};

/** Commodity category → localized label key (under the `market` namespace). */
export const CATEGORY_LABEL_KEY: Record<CommodityCategory, string> = {
  cereal: 'market.categoryCereal',
  pulse: 'market.categoryPulse',
  oilseed: 'market.categoryOilseed',
  vegetable: 'market.categoryVegetable',
  fruit: 'market.categoryFruit',
  spice: 'market.categorySpice',
  cash_crop: 'market.categoryCashCrop',
  other: 'market.categoryOther',
};

/** Price unit → localized label key. */
export const UNIT_LABEL_KEY: Record<PriceUnit, string> = {
  quintal: 'market.unitQuintal',
  kg: 'market.unitKg',
  tonne: 'market.unitTonne',
};

/** Search facet type → localized label key. */
export const SEARCH_TYPE_LABEL_KEY: Record<MarketSearchType, string> = {
  crop: 'market.searchTypeCrop',
  market: 'market.searchTypeMarket',
  district: 'market.searchTypeDistrict',
  state: 'market.searchTypeState',
};

/** Map a chosen search facet to the correct filter field. */
export const SEARCH_TYPE_TO_FILTER: Record<
  MarketSearchType,
  'crop' | 'market' | 'district' | 'state'
> = {
  crop: 'crop',
  market: 'market',
  district: 'district',
  state: 'state',
};
