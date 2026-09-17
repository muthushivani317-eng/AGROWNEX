import { useLocalSearchParams } from 'expo-router';

import { SoilRecommendationsScreen } from '@/features/soil';
import { useSelectedFarm } from '@/features/weather';

export default function SoilRecommendationsRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <SoilRecommendationsScreen farmId={resolved} />;
}
