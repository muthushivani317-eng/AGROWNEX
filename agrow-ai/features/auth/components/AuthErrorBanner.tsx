import { CircleAlert } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

export function AuthErrorBanner({ message, testID }: { message: string; testID?: string }) {
  const { colors } = useAppTheme();
  return (
    <View
      testID={testID}
      accessibilityRole="alert"
      style={[styles.banner, { borderColor: `${colors.danger}55`, backgroundColor: `${colors.danger}14` }]}
    >
      <CircleAlert size={20} color={colors.danger} />
      <AgText variant="bodySmall" color="danger" style={styles.message}>
        {message}
      </AgText>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    marginTop: 12,
    padding: 12,
    borderWidth: 1,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  message: { flex: 1 },
});
