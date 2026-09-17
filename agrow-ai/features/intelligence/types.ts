/**
 * Crop Intelligence Engine — the central farm-health assessment that aggregates
 * every module (Disease, Nutrient, Soil, Satellite, Weather, Growth, Calendar,
 * Expert) into one overall health score, a risk level and prioritized generic
 * recommendations. A module with no data is `null` — never fabricated
 * (docs/PRODUCT_RULES.md). Client-side camelCase mirror of the backend schemas.
 */

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type Priority = 'low' | 'medium' | 'high';

export type IssueSeverity = 'info' | 'advice' | 'warning' | 'critical';

/** The six health-scoring modules that feed the overall score. */
export type HealthModule =
  | 'disease'
  | 'nutrient'
  | 'soil'
  | 'satellite'
  | 'weather'
  | 'growth';

export interface HealthScores {
  overallHealthScore: number | null;
  confidence: number;
  diseaseScore: number | null;
  nutrientScore: number | null;
  soilScore: number | null;
  satelliteScore: number | null;
  weatherScore: number | null;
  growthScore: number | null;
}

export interface PriorityIssue {
  code: string;
  severity: IssueSeverity;
  modules: string[];
}

export interface Recommendation {
  code: string;
  priority: Priority;
  category: string;
  modules: string[];
}

export interface IntelligenceReport {
  id: string;
  farmId: string;
  crop: string | null;
  generatedAt: string;
  overallHealthScore: number | null;
  confidence: number;
  overallRisk: RiskLevel;
  riskScore: number | null;
  sourcesUsed: string[];
  health: HealthScores | null;
  priorityIssues: PriorityIssue[];
  recommendations: Recommendation[];
  createdAt: string;
  /** Client-only: a local (offline) report generated without a backend. */
  isSample?: boolean;
}

export interface IntelligenceDashboard {
  farmId: string;
  hasData: boolean;
  messageCode: string | null;
  report: IntelligenceReport | null;
}

export interface IntelligenceHistoryEntry {
  id: string;
  farmId: string;
  reportId: string | null;
  overallHealthScore: number | null;
  overallRisk: RiskLevel;
  confidence: number;
  recordedAt: string;
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
export interface ApiHealthScores {
  overall_health_score: number | null;
  confidence: number;
  disease_score: number | null;
  nutrient_score: number | null;
  soil_score: number | null;
  satellite_score: number | null;
  weather_score: number | null;
  growth_score: number | null;
}

export interface ApiPriorityIssue {
  code: string;
  severity: IssueSeverity;
  modules: string[];
}

export interface ApiRecommendation {
  code: string;
  priority: Priority;
  category: string;
  modules: string[];
}

export interface ApiIntelligenceReport {
  id: string;
  farm_id: string;
  crop: string | null;
  generated_at: string;
  overall_health_score: number | null;
  confidence: number;
  overall_risk: RiskLevel;
  risk_score: number | null;
  sources_used: string[];
  health: ApiHealthScores | null;
  priority_issues: ApiPriorityIssue[];
  recommendations: ApiRecommendation[];
  created_at: string;
}

export interface ApiIntelligenceDashboard {
  farm_id: string;
  has_data: boolean;
  message_code: string | null;
  report: ApiIntelligenceReport | null;
}

export interface ApiIntelligenceHistoryEntry {
  id: string;
  farm_id: string;
  report_id: string | null;
  overall_health_score: number | null;
  overall_risk: RiskLevel;
  confidence: number;
  recorded_at: string;
}

// --------------------------------------------------------------------------- //
// Engine inputs (pure client mirror of the backend signals).
// --------------------------------------------------------------------------- //
export interface DiseaseSignal {
  disease: string | null;
  confidence: number | null;
  severity: string | null; // none | low | moderate | high
  needsExpert?: boolean;
}

export interface NutrientSignal {
  primary: string | null;
  status: string | null; // confirmed | possible | not_confirmed
  confidence: number | null;
  severity: string | null; // none | mild | moderate | severe | unknown
  needsTest?: boolean;
}

export interface SoilSignal {
  hasData: boolean;
  nitrogen?: string | null;
  phosphorus?: string | null;
  potassium?: string | null;
  organicCarbon?: string | null;
  phClass?: string | null;
  salinity?: string | null;
  deficientMicronutrients?: string[];
  confidence?: number | null;
}

export interface SatelliteSignal {
  ndvi: number | null;
  vegetationHealth: string | null;
  stressLevel: string | null;
  moistureStatus: string | null;
  trend: string | null;
  confidence?: number | null;
  alertCodes?: string[];
}

export interface WeatherSignal {
  insightCodes: string[];
  rainProbabilityPct?: number | null;
}

export interface GrowthSignal {
  healthScore: number | null;
  healthDelta: number | null;
  riskLevel: string | null; // low | medium | high
}

export interface CalendarSignal {
  today: number;
  upcoming: number;
  missed: number;
}

export interface ExpertSignal {
  openConsultation: boolean;
}

export interface IntelligenceInputs {
  disease?: DiseaseSignal | null;
  nutrient?: NutrientSignal | null;
  soil?: SoilSignal | null;
  satellite?: SatelliteSignal | null;
  weather?: WeatherSignal | null;
  growth?: GrowthSignal | null;
  calendar?: CalendarSignal;
  expert?: ExpertSignal;
}
