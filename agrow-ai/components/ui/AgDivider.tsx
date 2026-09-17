import { View } from 'react-native';

import { cn } from '@/utils/cn';

import { AgText } from './AgText';

interface AgDividerProps {
  label?: string;
  className?: string;
}

export function AgDivider({ label, className }: AgDividerProps) {
  if (!label) return <View className={cn('h-px w-full bg-border', className)} />;
  return (
    <View className={cn('flex-row items-center gap-3', className)}>
      <View className="h-px flex-1 bg-border" />
      <AgText variant="caption" color="muted">
        {label}
      </AgText>
      <View className="h-px flex-1 bg-border" />
    </View>
  );
}
