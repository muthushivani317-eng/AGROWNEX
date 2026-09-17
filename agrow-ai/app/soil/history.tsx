import { useLocalSearchParams } from 'expo-router';

import { SoilHistoryScreen } from '@/features/soil';
import { useSelectedFarm } from '@/features/weather';

export default function SoilHistoryRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <SoilHistoryScreen farmId={resolved} />;
}
