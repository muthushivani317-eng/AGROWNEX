import { Redirect, useLocalSearchParams } from 'expo-router';
import { OrganicPlanScreen } from '@/features/organic';
import { organicFeatureEnabled } from '@/features/organic/featureFlag';
export default function OrganicPlanRoute() { const { farmId } = useLocalSearchParams<{ farmId?: string }>(); return organicFeatureEnabled && farmId ? <OrganicPlanScreen farmId={farmId}/> : <Redirect href="/farm"/>; }
