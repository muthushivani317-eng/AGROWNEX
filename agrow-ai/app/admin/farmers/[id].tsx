import { useLocalSearchParams } from 'expo-router';

import { FarmerDetailScreen } from '@/features/admin';

export default function AdminFarmerDetailRoute() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  if (!id) return null;
  return <FarmerDetailScreen userId={id} />;
}
