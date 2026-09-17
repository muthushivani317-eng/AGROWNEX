import {
  Bell,
  Brain,
  Bug,
  CalendarDays,
  CloudRain,
  Landmark,
  Layers,
  Leaf,
  LineChart,
  type LucideIcon,
  MessageCircle,
  MessagesSquare,
  Satellite,
  Sprout,
  TrendingUp,
} from 'lucide-react-native';

/** Source module → lucide icon (mirrors the Home quick-action icons). */
export const SOURCE_ICON: Record<string, LucideIcon> = {
  disease: Bug,
  nutrient: Leaf,
  soil: Layers,
  satellite: Satellite,
  growth: LineChart,
  weather: CloudRain,
  produce: Sprout,
  experts: MessagesSquare,
  schemes: Landmark,
  market: TrendingUp,
  ai_chat: MessageCircle,
  calendar: CalendarDays,
  iot: Bell,
};

export function sourceIcon(source: string): LucideIcon {
  return SOURCE_ICON[source] ?? Brain;
}
