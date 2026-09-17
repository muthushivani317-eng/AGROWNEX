import { Image } from 'expo-image';
import { MapPin } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { type LayoutChangeEvent, View } from 'react-native';
import Svg, { Circle, Polygon } from 'react-native-svg';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useTranslation } from 'react-i18next';

import type { FarmBoundary, FarmLocation, LatLng } from '../types';
import { polygonToRing } from '../utils/geo';
import { staticMapUrl } from '../utils/mapbox';
import { project, type Size } from '../utils/mercator';

/** Read-only map preview of a farm's boundary/location (detail screen). */
export function FarmMiniMap({
  boundary,
  location,
  height = 200,
  zoom = 16,
}: {
  boundary: FarmBoundary | null;
  location: FarmLocation | null;
  height?: number;
  zoom?: number;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [size, setSize] = useState<Size>({ width: 0, height });

  const center: LatLng | null = useMemo(() => {
    if (boundary?.centroidLat != null && boundary?.centroidLng != null) {
      return { latitude: boundary.centroidLat, longitude: boundary.centroidLng };
    }
    if (location?.latitude != null && location?.longitude != null) {
      return { latitude: location.latitude, longitude: location.longitude };
    }
    return null;
  }, [boundary, location]);

  const ring = useMemo(() => polygonToRing(boundary?.geojson ?? null), [boundary]);

  const onLayout = (e: LayoutChangeEvent) =>
    setSize({ width: e.nativeEvent.layout.width, height: e.nativeEvent.layout.height });

  if (!center) {
    return (
      <View
        style={{ height }}
        className="items-center justify-center rounded-card border border-border bg-surface"
      >
        <MapPin size={22} color={colors.textMuted} />
        <AgText variant="caption" color="muted" className="mt-1">
          {t('farm.noLocation')}
        </AgText>
      </View>
    );
  }

  const mapUrl =
    size.width > 0
      ? staticMapUrl({ center, zoom, width: size.width, height: size.height, retina: true })
      : null;
  const projected =
    size.width > 0 ? ring.map((v) => project(v, center, zoom, size)) : [];
  const pointsAttr = projected.map((p) => `${p.x},${p.y}`).join(' ');
  const centerPx = project(center, center, zoom, size);

  return (
    <View
      onLayout={onLayout}
      style={{ height }}
      className="overflow-hidden rounded-card border border-border bg-surface"
    >
      {mapUrl ? (
        <Image
          source={{ uri: mapUrl }}
          style={{ width: size.width, height: size.height }}
          contentFit="cover"
          transition={150}
        />
      ) : null}
      {size.width > 0 ? (
        <Svg
          width={size.width}
          height={size.height}
          style={{ position: 'absolute', left: 0, top: 0 }}
        >
          {projected.length >= 3 ? (
            <Polygon
              points={pointsAttr}
              fill={colors.primary}
              fillOpacity={0.25}
              stroke={colors.primary}
              strokeWidth={2}
            />
          ) : (
            <Circle
              cx={centerPx.x}
              cy={centerPx.y}
              r={7}
              fill={colors.primary}
              stroke={colors.onPrimary}
              strokeWidth={2}
            />
          )}
        </Svg>
      ) : null}
    </View>
  );
}
