import { X } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Image, Modal, Pressable, StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';

/** Full-screen image viewer for a consultation attachment. */
export function AttachmentViewer({
  uri,
  caption,
  onClose,
}: {
  uri: string | null;
  caption?: string | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal
      visible={Boolean(uri)}
      transparent
      animationType="fade"
      onRequestClose={onClose}
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
            resizeMode="contain"
            style={styles.image}
            accessibilityLabel={caption ?? t('experts.attachment')}
          />
        ) : null}
        {caption ? (
          <AgText center style={styles.caption}>
            {caption}
          </AgText>
        ) : null}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.90)',
  },
  closeButton: {
    position: 'absolute',
    top: 48,
    right: 20,
    zIndex: 10,
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  image: { width: '100%', height: '80%', borderRadius: 12 },
  caption: { marginTop: 12, color: '#FFFFFF' },
});
