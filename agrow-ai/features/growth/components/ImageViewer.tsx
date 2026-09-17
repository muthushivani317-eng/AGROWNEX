import { Image } from 'expo-image';
import { X } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Modal, Pressable, StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';

/** Full-screen image viewer modal (docs: image viewer). */
export function ImageViewer({
  uri,
  caption,
  visible,
  onClose,
}: {
  uri: string | null;
  caption?: string | null;
  visible: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal
      visible={visible && Boolean(uri)}
      transparent
      animationType="fade"
      onRequestClose={onClose}
      accessibilityViewIsModal
    >
      <View style={styles.backdrop}>
        <Pressable
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel={t('common.close')}
          style={styles.closeButton}
        >
          <X size={24} color="#fff" />
        </Pressable>
        {uri ? (
          <Image
            source={{ uri }}
            style={{ width: '100%', aspectRatio: 1 }}
            contentFit="contain"
          />
        ) : null}
        {caption ? (
          <AgText variant="bodySmall" center style={styles.caption}>
            {caption}
          </AgText>
        ) : null}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  // Deliberately fixed black media scrim; this is not an app-theme surface.
  backdrop: {
    flex: 1,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.90)',
  },
  closeButton: {
    position: 'absolute',
    top: 56,
    right: 20,
    zIndex: 10,
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  caption: { marginTop: 16, color: '#FFFFFF' },
});
