import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicConversionPlanScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
import { useSelectedFarm } from '@/features/weather';
// Same current-farm fallback as /organic/index.tsx and /organic/readiness.tsx.
export default function OrganicConversionPlanRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected, isLoading } = useSelectedFarm();
  const resolvedFarmId = farmId ?? selected?.id;
  if (!organicFeatureEnabled) return <Redirect href="/farm"/>;
  if (!resolvedFarmId) return isLoading ? null : <Redirect href="/farm"/>;
  return <OrganicConversionPlanScreen farmId={resolvedFarmId}/>;
}
