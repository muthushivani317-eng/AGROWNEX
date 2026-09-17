import { useLocalSearchParams } from 'expo-router';

import { IntelligenceHistoryScreen } from '@/features/intelligence';
import { useSelectedFarm } from '@/features/weather';

export default function IntelligenceHistoryRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <IntelligenceHistoryScreen farmId={resolved} />;
}
