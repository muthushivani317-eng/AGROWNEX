import { useRouter } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

/** A back row with a title and optional right accessory, reused by the screens. */
export function SoilBackHeader({ title, right }: { title: string; right?: ReactNode }) {
  const { colors } = useAppTheme();
  const { t } = useTranslation();
  const router = useRouter();
  return (
    <View className="flex-row items-center justify-between">
      <AgPressable
        onPress={() => router.back()}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={t('common.back')}
        className="h-10 flex-1 flex-row items-center gap-1"
      >
        <ArrowLeft size={22} color={colors.text} />
        <AgText variant="bodyLarge" weight="semibold" numberOfLines={1} className="flex-1">
          {title}
        </AgText>
      </AgPressable>
      {right ?? null}
    </View>
  );
}
