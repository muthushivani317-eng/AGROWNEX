import { useLocalSearchParams } from 'expo-router';

import { BoundaryEditorScreen } from '@/features/farm';

export default function FarmBoundaryRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <BoundaryEditorScreen farmId={id} />;
}
