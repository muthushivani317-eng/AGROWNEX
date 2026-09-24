import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicDashboardScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
import { useSelectedFarm } from '@/features/weather';
// Home's Quick Actions card links here with no query param -- same
// current-farm convention as /growth and /weather -- so this falls back to
// the app's shared selected-farm hook instead of requiring a farmId param.
// A farmId param (e.g. a future deep link from a farm's own detail screen)
// still wins when present.
export default function OrganicDashboardRoute() {
  const { farmId } = useLocalSearchParams<{ farmId?: string }>();
  const { selected, isLoading } = useSelectedFarm();
  const resolvedFarmId = farmId ?? selected?.id;
  if (!organicFeatureEnabled) return <Redirect href="/farm"/>;
  if (!resolvedFarmId) return isLoading ? null : <Redirect href="/farm"/>;
  return <OrganicDashboardScreen farmId={resolvedFarmId}/>;
}
