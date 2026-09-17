import { Platform } from 'react-native';

import { RouteResolvingScreen } from '@/features/startup/StartupScreens';
import { WebsiteLandingScreen } from '@/features/website/WebsiteLandingScreen';

/** Entry redirect — routes the user to the correct destination on cold start. */
export default function Index() {
  return Platform.OS === 'web' ? <WebsiteLandingScreen /> : <RouteResolvingScreen />;
}
