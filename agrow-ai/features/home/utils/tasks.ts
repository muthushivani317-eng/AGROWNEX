import type { FarmSummary } from '@/features/farm';
import type { WeatherBundle } from '@/features/weather';

import type { DashboardTask } from '../types';

/**
 * Deterministic, rule-based tasks for today (docs: Today's Tasks → rule-based).
 * Derived from the weather insights plus a light weekday rotation, so results
 * are reproducible and never fabricated. Pure function — unit-tested.
 */
export function generateTasks(
  weather: WeatherBundle | null,
  _farm: FarmSummary | null,
  now: Date = new Date(),
): DashboardTask[] {
  const codes = new Set(weather?.insights.map((i) => i.code) ?? []);
  const tasks: DashboardTask[] = [];

  // Irrigation
  if (codes.has('irrigation.recommended')) {
    tasks.push({ id: 'irrigate', labelKey: 'home.taskIrrigate', icon: 'irrigate', tone: 'primary' });
  } else if (codes.has('irrigation.hold')) {
    tasks.push({
      id: 'hold-irrigation',
      labelKey: 'home.taskHoldIrrigation',
      icon: 'irrigate',
      tone: 'info',
    });
  }

  // Spraying
  if (codes.has('spraying.good_window')) {
    tasks.push({ id: 'spray', labelKey: 'home.taskSpray', icon: 'spray', tone: 'primary' });
  } else if (codes.has('spraying.avoid_wind') || codes.has('spraying.avoid_rain')) {
    tasks.push({
      id: 'spray-delay',
      labelKey: 'home.taskSprayDelay',
      icon: 'spray',
      tone: 'warning',
    });
  }

  // Weather hazards
  if (codes.has('heavy_rain.expected') || codes.has('heavy_rain.severe')) {
    tasks.push({ id: 'drainage', labelKey: 'home.taskDrainage', icon: 'drainage', tone: 'warning' });
  }
  if (codes.has('heat_stress.high') || codes.has('heat_stress.extreme')) {
    tasks.push({ id: 'heat', labelKey: 'home.taskHeat', icon: 'heat', tone: 'danger' });
  }

  // Always inspect the crop.
  tasks.push({ id: 'inspect', labelKey: 'home.taskInspect', icon: 'inspect', tone: 'info' });

  // Weekly rotation keeps the list varied but deterministic.
  const day = now.getDay();
  if (day === 1 || day === 4) {
    tasks.push({ id: 'weed', labelKey: 'home.taskWeed', icon: 'weed', tone: 'info' });
  }
  if (day === 2 || day === 5) {
    tasks.push({
      id: 'fertilizer',
      labelKey: 'home.taskFertilizer',
      icon: 'fertilizer',
      tone: 'info',
    });
  }

  return tasks;
}
