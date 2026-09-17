import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicLogbookScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
export default function OrganicLogbookRoute() { const { farmId } = useLocalSearchParams<{ farmId?: string }>(); return organicFeatureEnabled && farmId ? <OrganicLogbookScreen farmId={farmId}/> : <Redirect href="/farm"/>; }
