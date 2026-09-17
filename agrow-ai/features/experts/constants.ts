import type {
  ConsultationCategory,
  ConsultationPriority,
  ConsultationStatus,
  ConsultationView,
  ExpertType,
} from './types';

export const EXPERTS_CACHE_KEY = 'agrowai.experts.cache';
export const CONSULTATION_CACHE_KEY = 'agrowai.consultations.cache';
export const CONSULTATION_LOCAL_KEY = 'agrowai.consultations.local';
export const EXPERTS_LOCAL_KEY = 'agrowai.experts.local';
export const CONSULTATION_OUTBOX_KEY = 'agrowai.consultations.outbox';

export const DEFAULT_PAGE_SIZE = 20;

export const expertKeys = {
  all: ['experts'] as const,
  list: (key: string) => ['experts', 'list', key] as const,
  detail: (id: string) => ['experts', 'detail', id] as const,
};

export const consultationKeys = {
  all: ['consultations'] as const,
  list: (key: string) => ['consultations', 'list', key] as const,
  pending: ['consultations', 'pending'] as const,
  history: ['consultations', 'history'] as const,
  detail: (id: string) => ['consultations', 'detail', id] as const,
};

export const CONSULTATION_VIEWS: ConsultationView[] = ['all', 'pending', 'history'];

export const VIEW_LABEL_KEY: Record<ConsultationView, string> = {
  all: 'experts.viewAll',
  pending: 'experts.viewPending',
  history: 'experts.viewHistory',
};

export const CATEGORIES: ConsultationCategory[] = [
  'crop_disease',
  'pest_control',
  'soil_health',
  'irrigation',
  'fertilizer',
  'weather',
  'market',
  'scheme',
  'seed',
  'organic',
  'general',
];

export const CATEGORY_LABEL_KEY: Record<ConsultationCategory, string> = {
  crop_disease: 'experts.categoryCropDisease',
  pest_control: 'experts.categoryPestControl',
  soil_health: 'experts.categorySoilHealth',
  irrigation: 'experts.categoryIrrigation',
  fertilizer: 'experts.categoryFertilizer',
  weather: 'experts.categoryWeather',
  market: 'experts.categoryMarket',
  scheme: 'experts.categoryScheme',
  seed: 'experts.categorySeed',
  organic: 'experts.categoryOrganic',
  general: 'experts.categoryGeneral',
};

export const PRIORITIES: ConsultationPriority[] = ['low', 'medium', 'high', 'urgent'];

export const PRIORITY_LABEL_KEY: Record<ConsultationPriority, string> = {
  low: 'experts.priorityLow',
  medium: 'experts.priorityMedium',
  high: 'experts.priorityHigh',
  urgent: 'experts.priorityUrgent',
};

export const PRIORITY_TONE: Record<
  ConsultationPriority,
  'neutral' | 'info' | 'warning' | 'danger'
> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  urgent: 'danger',
};

export const STATUS_LABEL_KEY: Record<ConsultationStatus, string> = {
  submitted: 'experts.statusSubmitted',
  assigned: 'experts.statusAssigned',
  in_progress: 'experts.statusInProgress',
  awaiting_farmer: 'experts.statusAwaitingFarmer',
  awaiting_expert: 'experts.statusAwaitingExpert',
  resolved: 'experts.statusResolved',
  closed: 'experts.statusClosed',
  cancelled: 'experts.statusCancelled',
};

export const STATUS_TONE: Record<
  ConsultationStatus,
  'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'
> = {
  submitted: 'neutral',
  assigned: 'primary',
  in_progress: 'info',
  awaiting_farmer: 'warning',
  awaiting_expert: 'info',
  resolved: 'success',
  closed: 'neutral',
  cancelled: 'danger',
};

export const EXPERT_TYPE_LABEL_KEY: Record<ExpertType, string> = {
  tnau: 'experts.typeTnau',
  kvk: 'experts.typeKvk',
  govt_officer: 'experts.typeGovt',
  kisan_call_centre: 'experts.typeKisan',
  agronomist: 'experts.typeAgronomist',
  private: 'experts.typePrivate',
};

/** Concluded statuses shown in the history view (mirrors the backend). */
export const HISTORY_STATUSES: ConsultationStatus[] = [
  'resolved',
  'closed',
  'cancelled',
];
