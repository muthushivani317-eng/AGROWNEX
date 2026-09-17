import { useRouter } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

import { AgErrorState, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
// Reuse the shared image picker + upload service (docs/CODING_STANDARDS → no duplication).
import { uploadService } from '@/features/profile/services/uploadProvider';
import { useAppTheme } from '@/hooks/useAppTheme';
import { pickProfileImage } from '@/utils/image';

import { FarmImageGallery } from '../components/FarmImageGallery';
import { useAddFarmImage, useFarmImages } from '../hooks/useFarmImages';

export function FarmGalleryScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();

  const { data: images, isLoading, isError, refetch } = useFarmImages(farmId);
  const addImage = useAddFarmImage(farmId);

  const onAddPhoto = async () => {
    const uri = await pickProfileImage();
    if (!uri) return;
    try {
      const url = await uploadService.uploadImage(uri, 'farms');
      await addImage.mutateAsync({ fileUrl: url, mimeType: 'image/jpeg' });
    } catch {
      Alert.alert(t('farm.uploadFailed'));
    }
  };

  return (
    <AgScreen scroll>
      <View className="mt-2 flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="-ml-2 h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('farm.galleryTitle')}
        </AgText>
      </View>

      {isLoading ? (
        <View className="mt-4 flex-row flex-wrap gap-2">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} className="aspect-square w-[31%] rounded-md" />
          ))}
        </View>
      ) : isError ? (
        <AgErrorState onRetry={() => void refetch()} />
      ) : (
        <View className="mt-4">
          <FarmImageGallery
            images={images ?? []}
            onAdd={onAddPhoto}
            adding={addImage.isPending}
          />
          {!images?.length ? (
            <AgText variant="bodySmall" color="muted" className="mt-4">
              {t('farm.noImagesMsg')}
            </AgText>
          ) : null}
        </View>
      )}
    </AgScreen>
  );
}
