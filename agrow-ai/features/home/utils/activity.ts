import type { AuthUser } from '@/features/auth';
import type { FarmSummary } from '@/features/farm';
import type { WeatherBundle } from '@/features/weather';

import type { ActivityItem } from '../types';

const MAX_ITEMS = 5;
const MAX_FARMS = 3;

/**
 * Recent activity derived from real data only (docs/PRODUCT_RULES → never
 * fabricate). Sources: the farmer's most recently updated farms, profile setup,
 * and any active weather alert. Pure function — unit-tested.
 */
export function buildRecentActivity(
  farms: FarmSummary[],
  user: AuthUser | null,
  weather: WeatherBundle | null,
): ActivityItem[] {
  const items: ActivityItem[] = [];

  const recentFarms = [...farms]
    .sort((a, b) => (b.updatedAt ?? '').localeCompare(a.updatedAt ?? ''))
    .slice(0, MAX_FARMS);
  for (const farm of recentFarms) {
    items.push({
      id: `farm-${farm.id}`,
      kind: 'farm',
      titleKey: 'home.activityFarm',
      params: { name: farm.name },
      timestamp: farm.updatedAt,
    });
  }

  if (user?.profileCompleted) {
    items.push({
      id: 'profile',
      kind: 'profile',
      titleKey: 'home.activityProfile',
      timestamp: user.createdAt ?? null,
    });
  }

  const alert = weather?.insights.find(
    (i) => i.severity === 'warning' || i.severity === 'critical',
  );
  if (alert) {
    items.push({
      id: 'weather-alert',
      kind: 'weather',
      titleKey: 'home.activityWeather',
      category: alert.category,
      timestamp: weather?.fetchedAt ?? null,
    });
  }

  return items
    .sort((a, b) => (b.timestamp ?? '').localeCompare(a.timestamp ?? ''))
    .slice(0, MAX_ITEMS);
}
