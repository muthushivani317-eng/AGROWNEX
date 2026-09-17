import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicDashboardScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
export default function OrganicDashboardRoute() { const { farmId } = useLocalSearchParams<{ farmId?: string }>(); return organicFeatureEnabled && farmId ? <OrganicDashboardScreen farmId={farmId}/> : <Redirect href="/farm"/>; }
