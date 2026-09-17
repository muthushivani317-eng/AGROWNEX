import { Redirect } from 'expo-router'; import { OrganicInputLibraryScreen } from '@/features/organic'; import { organicFeatureEnabled } from '@/features/organic/featureFlag';
export default function OrganicInputsRoute() { return organicFeatureEnabled ? <OrganicInputLibraryScreen/> : <Redirect href="/farm"/>; }
