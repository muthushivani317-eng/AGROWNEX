import { useLocalSearchParams } from 'expo-router';
import { ProduceTraceabilityScreen } from '@/features/produce/screens/ProduceTraceabilityScreen';
export default function TraceabilityRoute() { const { id } = useLocalSearchParams<{ id: string }>(); return <ProduceTraceabilityScreen offerId={id} />; }
