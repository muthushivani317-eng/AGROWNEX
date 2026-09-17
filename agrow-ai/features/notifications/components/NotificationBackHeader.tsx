import { useRouter } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';
import { notificationTheme as nt } from '../notificationTheme';

/** A back row with a title and optional right accessory, reused by the screens. */
export function NotificationBackHeader({
  title,
  right,
}: {
  title: string;
  right?: ReactNode;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  return (
    <View className="flex-row items-center justify-between">
      <AgPressable
        onPress={() => router.back()}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={t('common.back')}
        style={{ minHeight: 48, flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 }}
      >
        <ArrowLeft size={24} color={nt.ink} />
        <AgText variant="headingS" weight="bold" numberOfLines={1} className="flex-1" style={{ color: nt.ink }}>
          {title}
        </AgText>
      </AgPressable>
      {right ?? null}
    </View>
  );
}
