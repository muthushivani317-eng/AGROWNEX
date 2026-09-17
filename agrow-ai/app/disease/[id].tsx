import { useLocalSearchParams } from 'expo-router';

import { DiseaseDetailScreen } from '@/features/disease';

export default function DiseaseDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <DiseaseDetailScreen reportId={id} />;
}
