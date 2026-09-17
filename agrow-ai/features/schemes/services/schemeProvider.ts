import { buildProfile, isBackendConfigured } from "@/config/env";
import { mayUseLocalFeatureMocks } from "@/config/providerSafety";
import { logger } from "@/lib/logger";

import type {
  EligibleSchemes,
  RecommendedSchemes,
  SchemeDetail,
  SchemeListFilters,
  SchemePage,
  SchemeQuery,
  SchemeSummary,
  FarmerDocument,
  DocumentType,
} from "../types";

/**
 * Government scheme data source contract. Backed by the verified AgrowAI scheme
 * API + eligibility engine when a backend is configured, otherwise a local
 * offline provider that runs the same deterministic engine over verified sample
 * schemes client-side. Designed so a future verified source (Tamil Nadu portal,
 * Central APIs, Admin Portal, Scraper) can replace the backend with no frontend
 * change (docs: provider abstraction).
 */
export interface SchemeProvider {
  /** All verified schemes (filter by category/search, paginated). */
  list(filters: SchemeListFilters): Promise<SchemePage>;
  /** Schemes the farmer is eligible/likely-eligible for, ranked by score. */
  eligible(
    query: SchemeQuery,
    page?: number,
    pageSize?: number,
  ): Promise<EligibleSchemes>;
  /** The highest-scoring eligible schemes for the farmer. */
  recommended(query: SchemeQuery): Promise<RecommendedSchemes>;
  /** Full scheme detail with the farmer's eligibility, documents and steps. */
  detail(id: string, query: SchemeQuery): Promise<SchemeDetail>;
  /** The farmer's bookmarked schemes (with their current eligibility). */
  bookmarks(query: SchemeQuery): Promise<SchemeSummary[]>;
  addBookmark(schemeId: string): Promise<void>;
  removeBookmark(schemeId: string): Promise<void>;
  myDocuments(): Promise<FarmerDocument[]>;
  setMyDocument(
    documentType: DocumentType,
    hasDocument: boolean,
  ): Promise<FarmerDocument>;
}

export class SchemeError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "SchemeError";
  }
}

let provider: SchemeProvider | null = null;
const unavailable = async (): Promise<never> => {
  throw new SchemeError(
    "scheme_data_unavailable",
    "schemes.providerUnavailable",
  );
};
const unavailableSchemeProvider: SchemeProvider = {
  list: unavailable,
  eligible: unavailable,
  recommended: unavailable,
  detail: unavailable,
  bookmarks: unavailable,
  addBookmark: unavailable,
  removeBookmark: unavailable,
  myDocuments: unavailable,
  setMyDocument: unavailable,
};

export function getSchemeProvider(): SchemeProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiSchemeProvider")
      .apiSchemeProvider as SchemeProvider;
    logger.info("schemes", "using api provider");
  } else if (mayUseLocalFeatureMocks(buildProfile, isBackendConfigured)) {
    provider = require("./localSchemeProvider")
      .localSchemeProvider as SchemeProvider;
    logger.info("schemes", "using local provider");
  } else {
    provider = unavailableSchemeProvider;
    logger.warn("schemes", "backend unavailable; feature is fail-closed");
  }
  return provider;
}
