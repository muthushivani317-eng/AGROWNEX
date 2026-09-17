import { useLocalSearchParams } from 'expo-router';

import { MemoryDetailScreen } from '@/features/memory';

export default function MemoryDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  if (!id) return null;
  return <MemoryDetailScreen id={id} />;
}
