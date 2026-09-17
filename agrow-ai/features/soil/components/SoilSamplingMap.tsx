import { Image } from "expo-image";
import { useMemo, useState } from "react";
import { type LayoutChangeEvent, StyleSheet, View } from "react-native";
import { useTranslation } from "react-i18next";
import Svg, { Circle, Polygon } from "react-native-svg";
import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { polygonToRing } from "@/features/farm/utils/geo";
import { staticMapUrl } from "@/features/farm/utils/mapbox";
import { project, type Size } from "@/features/farm/utils/mercator";
import type { SoilScan } from "../types";
import { SOIL_UI } from "../design";

export function SoilSamplingMap({ scan }: { scan: SoilScan }) {
  const { colors } = useAppTheme();
  const { t } = useTranslation();
  const [size, setSize] = useState<Size>({ width: 0, height: 240 });
  const ring = useMemo(
    () => polygonToRing(scan.aoiGeojson as never),
    [scan.aoiGeojson],
  );
  const center = useMemo(() => {
    if (!ring.length) return null;
    return {
      latitude:
        ring.reduce((sum, point) => sum + point.latitude, 0) / ring.length,
      longitude:
        ring.reduce((sum, point) => sum + point.longitude, 0) / ring.length,
    };
  }, [ring]);
  const points = scan.samplingPlan?.points ?? [];
  if (!center || !points.length) return null;
  const onLayout = (event: LayoutChangeEvent) =>
    setSize({ width: event.nativeEvent.layout.width, height: 240 });
  const url = size.width
    ? staticMapUrl({ center, zoom: 16, width: size.width, height: 240 })
    : null;
  const polygon = ring.map((point) => project(point, center, 16, size));
  return (
    <View onLayout={onLayout} style={styles.container}>
      <View style={styles.map}>
        {url ? (
          <Image
            source={{ uri: url }}
            style={{ width: size.width, height: 240 }}
          />
        ) : null}
        {size.width ? (
          <Svg width={size.width} height={240} style={{ position: "absolute" }}>
            <Polygon
              points={polygon.map((point) => `${point.x},${point.y}`).join(" ")}
              fill={colors.primary}
              fillOpacity={0.12}
              stroke={colors.primary}
              strokeWidth={2}
            />
            {points.map((point) => {
              const pixel = project(
                { latitude: point.latitude, longitude: point.longitude },
                center,
                16,
                size,
              );
              return (
                <Circle
                  key={`${point.zoneId}:${point.latitude}:${point.longitude}`}
                  cx={pixel.x}
                  cy={pixel.y}
                  r={7}
                  fill={colors.warning}
                  stroke={colors.onPrimary}
                  strokeWidth={2}
                />
              );
            })}
          </Svg>
        ) : null}
      </View>
      <AgText variant="caption" style={styles.caption}>
        {t("soil.samplingLocationCount", { count: points.length })}
      </AgText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { height: 284, gap: 8 },
  map: {
    height: 240,
    overflow: "hidden",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surfaceSoft,
  },
  caption: { color: SOIL_UI.muted },
});
