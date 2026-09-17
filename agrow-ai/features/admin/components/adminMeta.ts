import {
  Activity,
  Bell,
  Brain,
  Bug,
  FlaskConical,
  Landmark,
  Layers,
  type LucideIcon,
  MessageCircle,
  MessagesSquare,
  Satellite,
  Sprout,
  Tractor,
  Users,
} from 'lucide-react-native';

/** Overview metric key → lucide icon (mirrors the module icons used across the app). */
export const METRIC_ICON: Record<string, LucideIcon> = {
  total_farmers: Users,
  total_farms: Tractor,
  active_users: Activity,
  today_ai_chats: MessageCircle,
  disease_reports: Bug,
  soil_reports: Layers,
  satellite_reports: Satellite,
  intelligence_reports: Brain,
  scheme_saves: Landmark,
  produce_listings: Sprout,
  expert_consultations: MessagesSquare,
  notifications_sent: Bell,
};

export function metricIcon(key: string): LucideIcon {
  return METRIC_ICON[key] ?? FlaskConical;
}

/** Compact number formatting for dashboard tiles (1.3k, 2.1M). */
export function formatCount(value: number | null): string {
  if (value == null) return '—';
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return `${value}`;
}

/** Kilograms → a readable weight (kg / t). */
export function formatKg(kg: number): string {
  if (kg >= 1000) return `${(kg / 1000).toFixed(1)} t`;
  return `${Math.round(kg)} kg`;
}

/** ISO → a stable, locale-neutral short date (never guesses a missing date). */
export function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const m = `${d.getUTCMonth() + 1}`.padStart(2, '0');
  const day = `${d.getUTCDate()}`.padStart(2, '0');
  return `${d.getUTCFullYear()}-${m}-${day}`;
}
