import { useLocalSearchParams } from 'expo-router';

import { UploadSoilReportScreen } from '@/features/soil';
import { useSelectedFarm } from '@/features/weather';

export default function UploadSoilRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected } = useSelectedFarm();
  const resolved = farmId ?? selected?.id;
  if (!resolved) return null;
  return <UploadSoilReportScreen farmId={resolved} />;
}
