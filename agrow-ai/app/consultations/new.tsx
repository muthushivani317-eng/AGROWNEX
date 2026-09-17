import { useLocalSearchParams } from 'expo-router';

import { CreateConsultationScreen } from '@/features/experts';

export default function CreateConsultationRoute() {
  const { expertId } = useLocalSearchParams<{ expertId?: string }>();
  return <CreateConsultationScreen expertId={expertId} />;
}
