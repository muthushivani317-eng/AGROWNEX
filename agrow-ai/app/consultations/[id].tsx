import { useLocalSearchParams } from 'expo-router';

import { ConsultationDetailScreen } from '@/features/experts';

export default function ConsultationDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <ConsultationDetailScreen id={id} />;
}
