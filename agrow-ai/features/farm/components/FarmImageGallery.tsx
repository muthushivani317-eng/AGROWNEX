import { Image } from 'expo-image';
import { ImagePlus } from 'lucide-react-native';
import { ActivityIndicator, View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useTranslation } from 'react-i18next';

import type { FarmImage } from '../types';

/** Responsive image grid with an optional "add photo" tile. */
export function FarmImageGallery({
  images,
  onAdd,
  adding = false,
}: {
  images: FarmImage[];
  onAdd?: () => void;
  adding?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  return (
    <View className="flex-row flex-wrap gap-2">
      {onAdd ? (
        <AgPressable
          onPress={onAdd}
          disabled={adding}
          accessibilityRole="button"
          accessibilityLabel={t('farm.addPhoto')}
          className="aspect-square w-[31%] items-center justify-center rounded-md border border-dashed border-border bg-surface-card"
        >
          {adding ? (
            <ActivityIndicator color={colors.primary} />
          ) : (
            <>
              <ImagePlus size={22} color={colors.primary} />
              <AgText variant="caption" color="primary" className="mt-1">
                {t('farm.addPhoto')}
              </AgText>
            </>
          )}
        </AgPressable>
      ) : null}
      {images.map((image) => (
        <Image
          key={image.id}
          source={{ uri: image.fileUrl }}
          style={{ borderRadius: 12 }}
          className="aspect-square w-[31%]"
          contentFit="cover"
          transition={150}
          accessibilityLabel={image.caption ?? t('farm.farmPhoto')}
        />
      ))}
    </View>
  );
}
