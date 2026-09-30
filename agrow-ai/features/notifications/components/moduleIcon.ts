import {
  Bell,
  Bot,
  Brain,
  CalendarDays,
  CloudRain,
  Landmark,
  Layers,
  Leaf,
  type LucideIcon,
  MessagesSquare,
  Recycle,
  Satellite,
  Stethoscope,
  Sprout,
  TrendingUp,
  Wheat,
} from 'lucide-react-native';

import type { NotificationModuleKey } from '../types';

/** Icon per event source (docs: the engine's modules). */
export const MODULE_ICON: Record<NotificationModuleKey, LucideIcon> = {
  weather: CloudRain,
  disease: Stethoscope,
  calendar: CalendarDays,
  growth: Sprout,
  market: TrendingUp,
  schemes: Landmark,
  produce: Wheat,
  ai: Bot,
  experts: MessagesSquare,
  soil: Layers,
  satellite: Satellite,
  nutrient: Leaf,
  intelligence: Brain,
  organic: Recycle,
  system: Bell,
};
