import { useLocalSearchParams } from 'expo-router';

import { FarmGalleryScreen } from '@/features/farm';

export default function FarmGalleryRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <FarmGalleryScreen farmId={id} />;
}
