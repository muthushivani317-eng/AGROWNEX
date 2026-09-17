import { Image } from 'expo-image';
import { StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';

export function AuthBrandHeader() {
  return (
    <View style={styles.container} accessibilityLabel="AgrowAI">
      <Image
        source={require('../../../assets/images/android-icon-foreground.png')}
        style={styles.logo}
        contentFit="contain"
        transition={0}
      />
      <View style={styles.wordmarkRow}>
        <AgText variant="headingL" weight="bold" style={styles.wordmark}>Agrow</AgText>
        <AgText variant="headingL" weight="bold" style={styles.ai}>AI</AgText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center' },
  logo: { width: 112, height: 112 },
  wordmarkRow: { marginTop: -12, flexDirection: 'row', alignItems: 'baseline' },
  wordmark: { color: '#185C32', letterSpacing: -1 },
  ai: { color: '#E7A100', letterSpacing: -1 },
});
