import { useLocalSearchParams } from 'expo-router';

import { SchemeDetailScreen } from '@/features/schemes';

export default function SchemeDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <SchemeDetailScreen schemeId={id} />;
}
