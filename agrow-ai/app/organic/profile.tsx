import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicProfileScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
export default function OrganicProfileRoute() { const { farmId } = useLocalSearchParams<{ farmId?: string }>(); return organicFeatureEnabled && farmId ? <OrganicProfileScreen farmId={farmId}/> : <Redirect href="/farm"/>; }
