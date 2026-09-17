import { buildProfile, isBackendConfigured } from "@/config/env";
import { mayUseLocalFeatureMocks } from "@/config/providerSafety";
import { logger } from "@/lib/logger";

import type {
  ProduceImageInput,
  ProduceInput,
  ProduceListParams,
  ProduceListResult,
  ProduceOffer,
  ProduceOfferDetail,
  FrozenBuyerOffer,
} from "../types";

/**
 * Produce data source contract. Backed by the AgrowAI produce API + Procurement
 * Engine when a backend is configured, otherwise a local offline provider that
 * runs the same deterministic engine over MMKV-stored offers. Designed so a
 * future procurement channel (eNAM, FPO, private buyers, export, admin portal)
 * can replace the backend with no frontend change (docs: provider abstraction).
 *
 * This is NOT a marketplace — the provider only collects and reads procurement
 * data; it never sells or fabricates buyers/prices.
 */
export interface ProduceProvider {
  list(params: ProduceListParams): Promise<ProduceListResult>;
  upcoming(page?: number, pageSize?: number): Promise<ProduceListResult>;
  history(page?: number, pageSize?: number): Promise<ProduceListResult>;
  get(id: string): Promise<ProduceOfferDetail>;
  create(input: ProduceInput): Promise<ProduceOfferDetail>;
  update(id: string, input: ProduceInput): Promise<ProduceOfferDetail>;
  remove(id: string): Promise<void>;
  addImage(id: string, image: ProduceImageInput): Promise<ProduceOfferDetail>;
  buyerOffer(id: string): Promise<FrozenBuyerOffer>;
  decideBuyerOffer(id: string, decision: 'accepted' | 'rejected', idempotencyKey: string, reason?: string): Promise<FrozenBuyerOffer>;
}

export class ProduceError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ProduceError";
  }
}

let provider: ProduceProvider | null = null;
const unavailable = async (): Promise<never> => {
  throw new ProduceError(
    "procurement_unavailable",
    "produce.procurementUnavailable",
  );
};
const unavailableProduceProvider: ProduceProvider = {
  list: unavailable,
  upcoming: unavailable,
  history: unavailable,
  get: unavailable,
  create: unavailable,
  update: unavailable,
  remove: unavailable,
  addImage: unavailable,
  buyerOffer: unavailable,
  decideBuyerOffer: unavailable,
};

export function getProduceProvider(): ProduceProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiProduceProvider")
      .apiProduceProvider as ProduceProvider;
    logger.info("produce", "using api provider");
  } else if (mayUseLocalFeatureMocks(buildProfile, isBackendConfigured)) {
    provider = require("./localProduceProvider")
      .localProduceProvider as ProduceProvider;
    logger.info("produce", "using local provider");
  } else {
    provider = unavailableProduceProvider;
    logger.warn("produce", "backend unavailable; feature is fail-closed");
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setProduceProvider(next: ProduceProvider | null): void {
  provider = next;
}

/** A no-op summary → offer helper kept here so both providers share the shape. */
export type { ProduceOffer };
