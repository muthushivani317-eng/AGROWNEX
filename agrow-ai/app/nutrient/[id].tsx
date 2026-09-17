import { useLocalSearchParams } from 'expo-router';

import { NutrientResultScreen } from '@/features/nutrient';

export default function NutrientResultRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <NutrientResultScreen reportId={id} />;
}
