import { Leaf, type LucideIcon } from 'lucide-react-native';
import { View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';

import { AgButton } from './AgButton';
import { AgText } from './AgText';

interface AgEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  /** Forces readable fixed colors when rendered on a light feature surface. */
  light?: boolean;
}

/** Friendly placeholder for lists/sections with no data yet. */
export function AgEmptyState({
  icon: Icon = Leaf,
  title,
  message,
  actionLabel,
  onAction,
  light = false,
}: AgEmptyStateProps) {
  const { colors } = useAppTheme();
  return (
    <View
      className="flex-1 items-center justify-center px-8 py-12"
      style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, paddingVertical: 48 }}
    >
      <View
        className="mb-4 h-20 w-20 items-center justify-center rounded-full"
        style={{ width: 80, height: 80, marginBottom: 16, borderRadius: 40, alignItems: 'center', justifyContent: 'center', backgroundColor: `${colors.primary}1A` }}
      >
        <Icon size={36} color={colors.primary} />
      </View>
      <AgText
        variant="headingS"
        weight="semibold"
        center
        style={light ? { color: '#173B2B' } : undefined}
      >
        {title}
      </AgText>
      {message ? (
        <AgText
          variant="body"
          color={light ? undefined : "muted"}
          center
          className="mt-2"
          style={light ? { color: '#5B6A64' } : undefined}
        >
          {message}
        </AgText>
      ) : null}
      {actionLabel && onAction ? (
        <AgButton
          light={light}
          title={actionLabel}
          onPress={onAction}
          variant="secondary"
          fullWidth={false}
          className="mt-5"
        />
      ) : null}
    </View>
  );
}
