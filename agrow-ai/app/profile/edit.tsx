import { CompleteProfileScreen } from '@/features/auth';

/** Edit profile reuses the onboarding flow, pre-filled from the saved record. */
export default function EditProfileRoute() {
  return <CompleteProfileScreen mode="edit" />;
}
