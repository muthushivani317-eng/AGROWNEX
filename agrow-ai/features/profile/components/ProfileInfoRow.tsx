import type { ReactNode } from 'react';
import { View } from 'react-native';

import { AgText } from '@/components/ui';

/** Icon + label + value row used to display read-only profile details. */
export function ProfileInfoRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value?: string | null;
}) {
  const display = value && value.trim() ? value : '—';
  return (
    <View className="flex-row items-center gap-3">
      <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
        {icon}
      </View>
      <View className="flex-1">
        <AgText variant="caption" color="muted">
          {label}
        </AgText>
        <AgText variant="body" weight="medium">
          {display}
        </AgText>
      </View>
    </View>
  );
}
