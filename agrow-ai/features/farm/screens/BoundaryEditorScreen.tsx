import { useRouter } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

import { AgButton, AgPressable, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { BoundaryEditor } from '../components/BoundaryEditor';
import { useBoundaryVertices } from '../hooks/useFarms';
import { useUpdateBoundary } from '../hooks/useBoundary';
import type { LatLng } from '../types';
import { ringToPolygon, validateRing } from '../utils/geo';

export function BoundaryEditorScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();

  const { vertices: initial, center, isLoading } = useBoundaryVertices(farmId);
  const [vertices, setVertices] = useState<LatLng[]>([]);
  const save = useUpdateBoundary(farmId);

  // Seed the editor from the farm's saved boundary exactly once, when it has
  // loaded. `initial` is a fresh array reference on every render (the hook
  // derives it inline), so depending on it directly would re-run this effect
  // every render and reset `vertices` to `initial` — wiping each point the
  // instant it is dropped. The ref guard makes the seed a one-shot.
  const seeded = useRef(false);
  useEffect(() => {
    if (isLoading || seeded.current) return;
    seeded.current = true;
    setVertices(initial);
  }, [isLoading, initial]);

  const onSave = () => {
    if (vertices.length < 3) {
      Alert.alert(t('farm.boundaryNeedsPoints'));
      return;
    }
    const check = validateRing(vertices);
    if (!check.ok) {
      Alert.alert(t(check.errorKey ?? 'farm.errorBoundaryPoints'));
      return;
    }
    save.mutate(
      { geojson: ringToPolygon(vertices), source: 'drawn' },
      {
        onSuccess: ({ offline }) => {
          Alert.alert(offline ? t('farm.savedOffline') : t('farm.boundarySaved'));
          router.back();
        },
        onError: () => Alert.alert(t('errors.generic')),
      },
    );
  };

  return (
    <AgScreen scroll contentClassName="pt-2">
      <View className="flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="-ml-2 h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('farm.boundaryTitle')}
        </AgText>
      </View>
      <AgText variant="body" color="muted" className="mt-1">
        {t('farm.boundarySubtitle')}
      </AgText>

      <View className="mt-5">
        {isLoading ? (
          <AgSkeleton className="h-80 w-full rounded-card" />
        ) : (
          <BoundaryEditor
            vertices={vertices}
            onChange={setVertices}
            initialCenter={center}
            height={380}
          />
        )}
      </View>

      <AgButton
        title={t('farm.saveBoundary')}
        onPress={onSave}
        loading={save.isPending}
        size="lg"
        className="mt-6"
      />
    </AgScreen>
  );
}
