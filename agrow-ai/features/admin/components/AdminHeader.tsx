import { useRouter } from 'expo-router';
import { ArrowLeft, type LucideIcon } from 'lucide-react-native';
import { View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

interface AdminHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  back?: boolean;
}

/** Consistent admin section header with an optional back affordance. */
export function AdminHeader({ icon: Icon, title, subtitle, back = false }: AdminHeaderProps) {
  const { colors } = useAppTheme();
  const router = useRouter();
  return (
    <View className="mt-2 gap-1">
      <View className="flex-row items-center gap-2">
        {back ? (
          <AgPressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel="Back"
            className="h-9 w-9 items-center justify-center rounded-full bg-surface-card"
          >
            <ArrowLeft size={20} color={colors.text} />
          </AgPressable>
        ) : (
          <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <Icon size={20} color={colors.primary} />
          </View>
        )}
        <AgText variant="headingL" weight="bold" className="flex-1">
          {title}
        </AgText>
      </View>
      {subtitle ? (
        <AgText variant="bodySmall" color="muted">
          {subtitle}
        </AgText>
      ) : null}
    </View>
  );
}
