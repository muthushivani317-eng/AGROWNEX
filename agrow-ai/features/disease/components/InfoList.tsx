import type { LucideIcon } from 'lucide-react-native';
import { View } from 'react-native';

import { AgCard, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

/** A titled card listing bullet items (symptoms, causes, actions, prevention). */
export function InfoList({
  icon: Icon,
  title,
  items,
}: {
  icon: LucideIcon;
  title: string;
  items: string[];
}) {
  const { colors } = useAppTheme();
  if (!items.length) return null;

  return (
    <View style={{ marginTop: 16 }}>
      <View style={{ marginBottom: 8, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <Icon size={16} color={colors.primary} />
        <AgText variant="label" weight="semibold" color="muted">
          {title}
        </AgText>
      </View>
      <AgCard style={{ gap: 8, backgroundColor: colors.surface, borderColor: colors.border }}>
        {items.map((item, index) => (
          <View key={index} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8 }}>
            <AgText variant="body" color="primary">
              •
            </AgText>
            <AgText variant="body" style={{ flex: 1 }}>
              {item}
            </AgText>
          </View>
        ))}
      </AgCard>
    </View>
  );
}
