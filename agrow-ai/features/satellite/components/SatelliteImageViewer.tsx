import { X } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Image, Modal, Pressable, StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';

import type { SatelliteImage } from '../types';

/** Full-screen viewer for a satellite scene image. */
export function SatelliteImageViewer({
  image,
  onClose,
}: {
  image: SatelliteImage | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal
      visible={Boolean(image)}
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
        {image ? (
          <Image
            source={{ uri: image.imageUrl }}
            resizeMode="contain"
            style={styles.image}
            accessibilityLabel={image.band}
          />
        ) : null}
        {image ? (
          <AgText center style={styles.caption}>
            {image.band}
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
