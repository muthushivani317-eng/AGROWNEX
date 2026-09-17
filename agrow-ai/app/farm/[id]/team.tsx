import { useLocalSearchParams } from 'expo-router';

import { FarmTeamScreen } from '@/features/farm/screens/FarmTeamScreen';

export default function FarmTeamRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <FarmTeamScreen farmId={id} />;
}
