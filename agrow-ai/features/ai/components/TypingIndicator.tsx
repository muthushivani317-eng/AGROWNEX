import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

function Dot({ delay, color }: { delay: number; color: string }) {
  const opacity = useSharedValue(0.3);
  useEffect(() => {
    opacity.value = withDelay(
      delay,
      withRepeat(withTiming(1, { duration: 450 }), -1, true),
    );
  }, [opacity, delay]);
  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));
  return (
    <Animated.View
      style={[style, { backgroundColor: color }]}
      className="h-2 w-2 rounded-full"
    />
  );
}

/** Assistant "thinking" indicator — three pulsing dots. */
export function TypingIndicator() {
  return (
    <View className="items-start">
      <View style={styles.bubble} className="flex-row items-center gap-1.5 px-4 py-3">
        <Dot delay={0} color="#58685F" />
        <Dot delay={150} color="#58685F" />
        <Dot delay={300} color="#58685F" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bubble: {
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#165B33',
    backgroundColor: '#FFFDF8',
  },
});
