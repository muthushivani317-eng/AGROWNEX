import { ActivityIndicator, View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';

import { AgText } from './AgText';

interface AgSpinnerProps {
  label?: string;
  size?: 'small' | 'large';
  fullscreen?: boolean;
}

export function AgSpinner({ label, size = 'large', fullscreen }: AgSpinnerProps) {
  const { colors } = useAppTheme();
  return (
    <View
      className={
        fullscreen
          ? 'flex-1 items-center justify-center bg-bg'
          : 'items-center justify-center py-8'
      }
    >
      <ActivityIndicator size={size} color={colors.primary} />
      {label ? (
        <AgText variant="bodySmall" color="muted" className="mt-3">
          {label}
        </AgText>
      ) : null}
    </View>
  );
}
