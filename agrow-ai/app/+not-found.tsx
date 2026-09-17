import { Link, Stack } from 'expo-router';
import { Leaf } from 'lucide-react-native';
import { View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

export default function NotFound() {
  const { colors } = useAppTheme();
  return (
    <>
      <Stack.Screen options={{ title: 'Not Found' }} />
      <View className="flex-1 items-center justify-center bg-bg px-8">
        <Leaf size={48} color={colors.primary} />
        <AgText variant="headingM" weight="bold" center className="mt-4">
          This screen doesn&apos;t exist.
        </AgText>
        <Link href="/" className="mt-4">
          <AgText variant="body" weight="semibold" color="primary">
            Go to home
          </AgText>
        </Link>
      </View>
    </>
  );
}
