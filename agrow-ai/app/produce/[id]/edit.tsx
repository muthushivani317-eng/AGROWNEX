import { useLocalSearchParams } from 'expo-router';

import { EditProduceScreen } from '@/features/produce';

export default function EditProduceRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <EditProduceScreen offerId={id} />;
}
