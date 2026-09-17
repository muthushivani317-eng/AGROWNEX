import { useLocalSearchParams } from 'expo-router';

import { NotificationDetailScreen } from '@/features/notifications';

export default function NotificationDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <NotificationDetailScreen id={id} />;
}
