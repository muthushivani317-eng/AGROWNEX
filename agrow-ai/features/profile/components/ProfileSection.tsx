import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { AgCard, AgText } from '@/components/ui';

/** A titled card grouping related profile rows (View & Settings screens). */
export function ProfileSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <View className="mt-5" style={styles.section}>
      <AgText variant="label" weight="semibold" color="muted" className="mb-2">
        {title}
      </AgText>
      <AgCard className="gap-4" style={styles.card}>{children}</AgCard>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { marginTop: 20 },
  card: { gap: 16 },
});
