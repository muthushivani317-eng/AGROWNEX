import { Image } from 'expo-image';
import { UserRound } from 'lucide-react-native';
import { View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';
import { cn } from '@/utils/cn';
import { initials } from '@/utils/format';

import { AgText } from './AgText';

interface AgAvatarProps {
  uri?: string | null;
  name?: string | null;
  size?: number;
  className?: string;
  light?: boolean;
}

/** Circular avatar showing a photo when available, otherwise name initials. */
export function AgAvatar({ uri, name, size = 64, className, light = false }: AgAvatarProps) {
  const { colors } = useAppTheme();
  const dimension = {
    width: size,
    height: size,
    borderRadius: size / 2,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    overflow: 'hidden' as const,
  };
  const avatarInitials = initials(name);

  if (uri) {
    return (
      <Image
        source={{ uri }}
        style={dimension}
        contentFit="cover"
        transition={150}
        accessibilityRole="image"
      />
    );
  }

  return (
    <View
      className={cn('items-center justify-center', className)}
      style={[dimension, { backgroundColor: light ? '#FFFDF8' : colors.card, borderColor: light ? '#B9CCBC' : colors.border, borderWidth: 1.5 }]}
    >
      {avatarInitials ? <AgText
        weight="bold"
        color="primary"
        style={{
          width: size,
          fontSize: Math.round(size * 0.36),
          lineHeight: Math.round(size * 0.44),
          textAlign: 'center',
          includeFontPadding: false,
        }}
      >
        {avatarInitials}
      </AgText> : <UserRound size={Math.round(size * 0.44)} color={light ? '#58685F' : colors.textMuted} />}
    </View>
  );
}
