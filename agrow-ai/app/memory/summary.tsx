import { useLocalSearchParams } from 'expo-router';

import { MemorySummaryScreen } from '@/features/memory';
import { useSelectedFarm } from '@/features/weather';

export default function MemorySummaryRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <MemorySummaryScreen farmId={resolved} />;
}
