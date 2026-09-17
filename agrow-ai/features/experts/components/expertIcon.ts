import {
  Building2,
  GraduationCap,
  Landmark,
  Leaf,
  type LucideIcon,
  Phone,
  UserRound,
} from 'lucide-react-native';

import type { ExpertType } from '../types';

/** Icon per verified expert desk type. */
export const EXPERT_TYPE_ICON: Record<ExpertType, LucideIcon> = {
  tnau: GraduationCap,
  kvk: Building2,
  govt_officer: Landmark,
  kisan_call_centre: Phone,
  agronomist: Leaf,
  private: UserRound,
};

export function expertTypeIcon(type: string): LucideIcon {
  return EXPERT_TYPE_ICON[type as ExpertType] ?? UserRound;
}
