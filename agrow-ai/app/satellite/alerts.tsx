import { useLocalSearchParams } from 'expo-router';

import { SatelliteAlertsScreen } from '@/features/satellite';
import { useSelectedFarm } from '@/features/weather';

export default function SatelliteAlertsRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <SatelliteAlertsScreen farmId={resolved} />;
}
