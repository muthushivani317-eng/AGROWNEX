import { useLocalSearchParams } from 'expo-router';

import { IntelligenceReportScreen } from '@/features/intelligence';

export default function IntelligenceReportRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  if (!id) return null;
  return <IntelligenceReportScreen reportId={id} />;
}
