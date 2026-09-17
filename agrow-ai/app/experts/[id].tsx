import { useLocalSearchParams } from 'expo-router';

import { ExpertProfileScreen } from '@/features/experts';

export default function ExpertProfileRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <ExpertProfileScreen id={id} />;
}
