import { buildProfile, isBackendConfigured } from "@/config/env";
import { mayUseLocalFeatureMocks } from "@/config/providerSafety";
import { logger } from "@/lib/logger";

import type {
  ChatInput,
  ChatResult,
  Conversation,
  ConversationDetail,
} from "../types";

/**
 * AI data source contract. Backed by the AgrowAI AI API (Gemini) when a backend
 * is configured, otherwise a local, offline provider with deterministic replies
 * (mirrors the auth/profile/farm/weather providers).
 */
export interface AIProvider {
  chat(input: ChatInput): Promise<ChatResult>;
  listConversations(): Promise<Conversation[]>;
  getConversation(id: string): Promise<ConversationDetail>;
  deleteConversation(id: string): Promise<void>;
}

export class AIError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "AIError";
  }
}

let provider: AIProvider | null = null;
const unavailable = async (): Promise<never> => {
  throw new AIError("ai_unavailable", "ai.providerUnavailable");
};
const unavailableAIProvider: AIProvider = {
  chat: unavailable,
  listConversations: unavailable,
  getConversation: unavailable,
  deleteConversation: unavailable,
};

export function getAIProvider(): AIProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiAIProvider").apiAIProvider as AIProvider;
    logger.info("ai", "using api provider");
  } else if (mayUseLocalFeatureMocks(buildProfile, isBackendConfigured)) {
    provider = require("./localAIProvider").localAIProvider as AIProvider;
    logger.info("ai", "using local provider");
  } else {
    provider = unavailableAIProvider;
    logger.warn("ai", "backend unavailable; feature is fail-closed");
  }
  return provider;
}
