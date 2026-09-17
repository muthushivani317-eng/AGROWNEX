import { useLocalSearchParams } from 'expo-router';

import { MemoryTimelineScreen } from '@/features/memory';
import { useSelectedFarm } from '@/features/weather';

export default function MemoryHistoryRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <MemoryTimelineScreen farmId={resolved} />;
}
