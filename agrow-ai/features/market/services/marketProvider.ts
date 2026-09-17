import { buildProfile, isBackendConfigured } from "@/config/env";
import { mayUseLocalFeatureMocks } from "@/config/providerSafety";
import { logger } from "@/lib/logger";

import type {
  AddFavouriteInput,
  MarketFavourite,
  MarketFilters,
  MarketHistory,
  MarketPricePage,
  MarketSearchResult,
} from "../types";

/**
 * Market data source contract. Backed by the verified AgrowAI market API when a
 * backend is configured, otherwise a local, offline provider that serves the
 * same deterministic sample prices client-side (mirrors the app's swappable
 * providers). Designed so a future price source can replace the backend with no
 * frontend change.
 */
export interface MarketProvider {
  prices(filters: MarketFilters): Promise<MarketPricePage>;
  history(
    crop: string,
    market: string,
    district?: string | null,
  ): Promise<MarketHistory>;
  search(term: string): Promise<MarketSearchResult[]>;
  favourites(): Promise<MarketFavourite[]>;
  addFavourite(input: AddFavouriteInput): Promise<MarketFavourite>;
  removeFavourite(id: string): Promise<void>;
}

export class MarketError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "MarketError";
  }
}

let provider: MarketProvider | null = null;
const unavailable = async (): Promise<never> => {
  throw new MarketError(
    "market_data_unavailable",
    "market.providerUnavailable",
  );
};
const unavailableMarketProvider: MarketProvider = {
  prices: unavailable,
  history: unavailable,
  search: unavailable,
  favourites: unavailable,
  addFavourite: unavailable,
  removeFavourite: unavailable,
};

export function getMarketProvider(): MarketProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiMarketProvider")
      .apiMarketProvider as MarketProvider;
    logger.info("market", "using api provider");
  } else if (mayUseLocalFeatureMocks(buildProfile, isBackendConfigured)) {
    provider = require("./localMarketProvider")
      .localMarketProvider as MarketProvider;
    logger.info("market", "using local provider");
  } else {
    provider = unavailableMarketProvider;
    logger.warn("market", "backend unavailable; feature is fail-closed");
  }
  return provider;
}
