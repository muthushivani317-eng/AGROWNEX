import { useLocalSearchParams } from 'expo-router';

import { FarmFormScreen } from '@/features/farm';

export default function EditFarmRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <FarmFormScreen farmId={id} />;
}
