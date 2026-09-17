import { useLocalSearchParams } from 'expo-router';

import { FarmDetailsScreen } from '@/features/farm';

export default function FarmDetailsRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <FarmDetailsScreen farmId={id} />;
}
