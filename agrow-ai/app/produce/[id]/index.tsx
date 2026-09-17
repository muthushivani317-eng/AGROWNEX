import { useLocalSearchParams } from 'expo-router';

import { ProduceDetailScreen } from '@/features/produce';

export default function ProduceDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <ProduceDetailScreen offerId={id} />;
}
