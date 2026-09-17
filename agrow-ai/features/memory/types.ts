/**
 * Farm Memory Engine — AgrowAI's long-term agricultural memory. NOT a chat history:
 * a structured, deterministic record of what happened on a farm over months and years,
 * learned from every module (Disease, Growth, Weather, Satellite, Soil, Nutrient,
 * Schemes, Market, Experts, AI Chat, Produce). Missing history is never fabricated
 * (docs/PRODUCT_RULES.md). Client-side camelCase mirror of the backend schemas.
 */

export type MemoryImportance = 'low' | 'medium' | 'high' | 'critical';

export type ObservationKind = 'observed' | 'inferred';

export type MemoryLinkType = 'follows' | 'relates' | 'resolves';

export type SummaryPeriod = 'season' | 'year';

export type MemorySource =
  | 'disease'
  | 'growth'
  | 'weather'
  | 'satellite'
  | 'soil'
  | 'nutrient'
  | 'schemes'
  | 'market'
  | 'experts'
  | 'ai_chat'
  | 'produce'
  | 'calendar'
  | 'iot';

export interface MemoryLink {
  id: string;
  fromMemoryId: string;
  toMemoryId: string;
  linkType: MemoryLinkType;
}

export interface FarmMemory {
  id: string;
  farmId: string;
  sourceModule: string;
  eventType: string;
  /** Localization code (Tamil-first client renders it with `params`). */
  summary: string;
  params: Record<string, unknown> | null;
  confidence: number | null;
  importance: MemoryImportance;
  importanceScore: number;
  observation: ObservationKind;
  season: string | null;
  seasonYear: number | null;
  crop: string | null;
  location: string | null;
  occurredAt: string;
  createdAt: string;
  tags: string[];
  occurrences: number;
  links: MemoryLink[];
  /** Client-only: a local (offline / dev) memory, never mistaken for a verified one. */
  isSample?: boolean;
}

export interface MemorySummary {
  id: string;
  farmId: string;
  periodType: SummaryPeriod;
  periodKey: string;
  season: string | null;
  year: number;
  crop: string | null;
  summary: string;
  params: Record<string, unknown> | null;
  highlights: string[];
  eventCount: number;
  importance: MemoryImportance;
  generatedAt: string;
}

export interface MemoryDashboard {
  farmId: string;
  hasData: boolean;
  total: number;
  messageCode: string | null;
  recent: FarmMemory[];
  latestSummary: MemorySummary | null;
}

export interface MemorySummaryBundle {
  farmId: string;
  seasons: MemorySummary[];
  years: MemorySummary[];
}

export interface MemoryRebuildResult {
  farmId: string;
  created: number;
  total: number;
  summaries: number;
  links: number;
}

export interface MemoryHistoryFilter {
  sourceModule?: string;
  season?: string;
  crop?: string;
  importance?: MemoryImportance;
  q?: string;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiMemoryLink {
  id: string;
  from_memory_id: string;
  to_memory_id: string;
  link_type: MemoryLinkType;
}

export interface ApiFarmMemory {
  id: string;
  farm_id: string;
  source_module: string;
  event_type: string;
  summary: string;
  params: Record<string, unknown> | null;
  confidence: number | null;
  importance: MemoryImportance;
  importance_score: number;
  observation: ObservationKind;
  season: string | null;
  season_year: number | null;
  crop: string | null;
  location: string | null;
  occurred_at: string;
  created_at: string;
  tags: string[];
  occurrences: number;
  links: ApiMemoryLink[];
}

export interface ApiMemorySummary {
  id: string;
  farm_id: string;
  period_type: SummaryPeriod;
  period_key: string;
  season: string | null;
  year: number;
  crop: string | null;
  summary: string;
  params: Record<string, unknown> | null;
  highlights: string[];
  event_count: number;
  importance: MemoryImportance;
  generated_at: string;
}

export interface ApiMemoryDashboard {
  farm_id: string;
  has_data: boolean;
  total: number;
  message_code: string | null;
  recent: ApiFarmMemory[];
  latest_summary: ApiMemorySummary | null;
}

export interface ApiMemorySummaryBundle {
  farm_id: string;
  seasons: ApiMemorySummary[];
  years: ApiMemorySummary[];
}

export interface ApiMemoryRebuildResult {
  farm_id: string;
  created: number;
  total: number;
  summaries: number;
  links: number;
}

// --------------------------------------------------------------------------- //
// Engine drafts (pure client mirror used by the local/offline provider).
// --------------------------------------------------------------------------- //
export interface MemoryEventDraft {
  sourceModule: string;
  eventType: string;
  occurredAt: string;
  summary: string;
  importance: MemoryImportance;
  observation: ObservationKind;
  confidence: number | null;
  crop: string | null;
  location: string | null;
  sourceRef: string | null;
  params: Record<string, unknown>;
  detail: string | null;
  tags: string[];
}
