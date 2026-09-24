import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicReadinessScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
import { useSelectedFarm } from '@/features/weather';
// Same current-farm fallback as /organic/index.tsx.
export default function OrganicReadinessRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected, isLoading } = useSelectedFarm();
  const resolvedFarmId = farmId ?? selected?.id;
  if (!organicFeatureEnabled) return <Redirect href="/farm"/>;
  if (!resolvedFarmId) return isLoading ? null : <Redirect href="/farm"/>;
  return <OrganicReadinessScreen farmId={resolvedFarmId}/>;
}
