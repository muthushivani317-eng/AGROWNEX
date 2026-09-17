import { useEffect } from 'react';
import { View, type ViewProps } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { cn } from '@/utils/cn';

interface AgSkeletonProps extends ViewProps {
  className?: string;
}

/** Shimmering placeholder block for building skeleton loading screens. */
export function AgSkeleton({ className, ...rest }: AgSkeletonProps) {
  const opacity = useSharedValue(0.5);

  useEffect(() => {
    opacity.value = withRepeat(withTiming(1, { duration: 800 }), -1, true);
  }, [opacity]);

  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return (
    <Animated.View style={style} {...rest}>
      <View className={cn('rounded-md bg-border/70', className)} />
    </Animated.View>
  );
}
