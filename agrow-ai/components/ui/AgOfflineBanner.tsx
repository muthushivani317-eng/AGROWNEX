import { CloudOff } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import Animated, { FadeInUp, FadeOutUp } from 'react-native-reanimated';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { AgText } from './AgText';

/** App-wide banner shown while there is no connectivity. */
export function AgOfflineBanner() {
  const { isConnected } = useNetworkStatus();
  const { t } = useTranslation();

  if (isConnected) return null;

  return (
    <Animated.View entering={FadeInUp} exiting={FadeOutUp}>
      <View className="flex-row items-center justify-center gap-2 bg-danger px-4 py-2">
        <CloudOff size={15} color="#fff" />
        <AgText variant="caption" weight="semibold" color="onPrimary">
          {t('common.offline')}
        </AgText>
      </View>
    </Animated.View>
  );
}
