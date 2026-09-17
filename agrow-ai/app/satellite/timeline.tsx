import { useLocalSearchParams } from 'expo-router';

import { SatelliteTimelineScreen } from '@/features/satellite';
import { useSelectedFarm } from '@/features/weather';

export default function SatelliteTimelineRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <SatelliteTimelineScreen farmId={resolved} />;
}
