import { Image } from 'expo-image';
import { Info, Locate, Map, Minus, Plus, RefreshCw, Trash2, Undo2 } from 'lucide-react-native';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable as AgPressable, type LayoutChangeEvent, StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
} from 'react-native-reanimated';
import Svg, { Circle, Line, Polygon, Polyline } from 'react-native-svg';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useTranslation } from 'react-i18next';

import {
  DEFAULT_MAP_CENTER,
  DEFAULT_MAP_ZOOM,
  MAX_MAP_ZOOM,
  MIN_MAP_ZOOM,
} from '../constants';
import { useCurrentLocation } from '../hooks/useCurrentLocation';
import type { LatLng } from '../types';
import { centroid, geodesicAreaSqm, hectaresToAcres, sqmToHectares } from '../utils/geo';
import { isMapboxConfigured, staticMapUrl } from '../utils/mapbox';
import { panCenter, project, unproject, type Size } from '../utils/mercator';

export interface BoundaryEditorProps {
  vertices: LatLng[];
  onChange: (vertices: LatLng[]) => void;
  onCenterChange?: (center: LatLng) => void;
  initialCenter?: LatLng | null;
  height?: number;
}

function ControlButton({
  icon,
  onPress,
  label,
}: {
  icon: React.ReactNode;
  onPress: () => void;
  label: string;
}) {
  return (
    <AgPressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={styles.mapControl}
    >
      {icon}
    </AgPressable>
  );
}

/**
 * Interactive farm-boundary editor (docs: MAPS). Renders a Mapbox static-tile
 * backdrop (or a grid when no token) with an SVG polygon overlay. Pan the map
 * under the fixed crosshair and tap "Drop" to add each corner; area is computed
 * live. GPS recentres on the farmer's location.
 */
export function BoundaryEditor({
  vertices,
  onChange,
  onCenterChange,
  initialCenter,
  height = 340,
}: BoundaryEditorProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { getCurrentLocation, loading: locating, error: locationError } = useCurrentLocation();

  const [size, setSize] = useState<Size>({ width: 0, height });
  const [center, setCenter] = useState<LatLng>(
    initialCenter ?? centroid(vertices) ?? DEFAULT_MAP_CENTER,
  );
  // The centre the currently-displayed tile is drawn for. It lags `center`
  // during a pan: we advance `center` (so the new tile URL is requested)
  // immediately, but keep projecting the SVG overlay against `renderedCenter`
  // until that new tile finishes loading. Combined with the held pan offset,
  // this keeps the tile and the polygon vertices pinned to the same screen
  // pixels straight through the swap — no "jump back" (see commitPan/onTileLoad).
  const [renderedCenter, setRenderedCenter] = useState<LatLng>(center);
  const [zoom, setZoom] = useState(DEFAULT_MAP_ZOOM);
  const [tileState, setTileState] = useState<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const [tileAttempt, setTileAttempt] = useState(0);

  useEffect(() => {
    if (initialCenter) {
      setCenter(initialCenter);
      setRenderedCenter(initialCenter);
    }
  }, [initialCenter?.latitude, initialCenter?.longitude]);

  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height: h } = e.nativeEvent.layout;
    setSize({ width, height: h });
  };

  const setCenterAndNotify = (next: LatLng) => {
    setCenter(next);
    onCenterChange?.(next);
  };

  // Advance the logical centre to the panned position, but DON'T zero the
  // dragged offset here — the new Mapbox tile for `next` loads asynchronously,
  // so snapping translate to 0 now would slam the still-visible OLD tile back
  // to its untranslated position (the "jump back"). We keep the offset in place
  // and let onTileLoad zero it the instant the new tile paints. When Mapbox is
  // not configured we render a static grid instead of an <Image>, so there is
  // no load event to wait for — snap immediately in that case.
  const commitPan = (dx: number, dy: number) => {
    const next = panCenter(center, dx, dy, zoom);
    setCenter(next);
    onCenterChange?.(next);
    if (!isMapboxConfigured) {
      setRenderedCenter(next);
      translateX.value = 0;
      translateY.value = 0;
    }
  };

  // Fires when the newly-requested tile has fully loaded. We swap the overlay's
  // projection origin to the new centre and zero the held pan offset in the same
  // commit, so "old tile + pan offset" becomes "new tile + zero offset" with the
  // tile and every vertex landing on the exact same screen pixels — no visible
  // jump. For non-pan updates (zoom/GPS/initial) the offset is already 0 and
  // renderedCenter already equals center, so this is a harmless no-op.
  const onTileLoad = () => {
    setRenderedCenter(center);
    translateX.value = 0;
    translateY.value = 0;
  };

  const pan = Gesture.Pan()
    .onUpdate((e) => {
      translateX.value = e.translationX;
      translateY.value = e.translationY;
    })
    .onEnd((e) => {
      runOnJS(commitPan)(e.translationX, e.translationY);
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }, { translateY: translateY.value }],
  }));

  const mapUrl = useMemo(
    () =>
      size.width > 0
        ? staticMapUrl({
            center,
            zoom,
            width: size.width,
            height: size.height,
            retina: true,
          })
        : null,
    [center, zoom, size],
  );

  useEffect(() => {
    setTileState(mapUrl ? 'loading' : 'idle');
  }, [mapUrl, tileAttempt]);

  const projected = useMemo(
    () =>
      size.width > 0
        ? vertices.map((v) => project(v, renderedCenter, zoom, size))
        : [],
    [vertices, renderedCenter, zoom, size],
  );

  const pointsAttr = projected.map((p) => `${p.x},${p.y}`).join(' ');
  const areaHa = sqmToHectares(geodesicAreaSqm(vertices));

  const HIT_RADIUS = 22;
  const handleMapTap = (x: number, y: number) => {
    const hitIndex = projected.findIndex(
      (p) => Math.hypot(p.x - x, p.y - y) <= HIT_RADIUS,
    );
    if (hitIndex !== -1) {
      onChange(vertices.filter((_, i) => i !== hitIndex));
      return;
    }
    const point = unproject({ x, y }, renderedCenter, zoom, size);
    onChange([...vertices, point]);
  };
  const tap = Gesture.Tap()
    .maxDuration(250)
    .onEnd((e, success) => {
      if (success) runOnJS(handleMapTap)(e.x, e.y);
    });
  const composedGesture = Gesture.Race(tap, pan);
  const undo = () => onChange(vertices.slice(0, -1));
  const clear = () => onChange([]);
  const changeZoom = (delta: number) =>
    setZoom((z) => Math.max(MIN_MAP_ZOOM, Math.min(MAX_MAP_ZOOM, z + delta)));

  const useGps = async () => {
    const loc = await getCurrentLocation();
    if (loc) {
      setZoom((z) => Math.max(z, 17));
      setCenterAndNotify({ latitude: loc.latitude, longitude: loc.longitude });
    }
  };

  const cx = size.width / 2;
  const cy = size.height / 2;

  return (
    <View>
      <View
        onLayout={onLayout}
        style={[styles.map, { height }]}
      >
        <GestureDetector gesture={composedGesture}>
          <Animated.View style={[{ flex: 1 }, animatedStyle]}>
            <GridBackdrop size={size} color={colors.border} />
            {mapUrl && tileState !== 'error' ? (
              <Image
                key={`${mapUrl}:${tileAttempt}`}
                source={{ uri: mapUrl }}
                style={styles.mapImage}
                contentFit="cover"
                cachePolicy="memory-disk"
                priority="high"
                // Instant swap (no crossfade): onTileLoad zeroes the held pan
                // offset the moment the new tile paints, so the tile and overlay
                // realign in a single frame. A fade would keep the old tile
                // visible at the reset offset for 150ms — the jump we're fixing.
                transition={0}
                onLoad={() => {
                  setTileState('loaded');
                  onTileLoad();
                }}
                onError={() => setTileState('error')}
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
                    fillOpacity={0.22}
                    stroke={colors.primary}
                    strokeWidth={2}
                  />
                ) : projected.length === 2 ? (
                  <Polyline
                    points={pointsAttr}
                    fill="none"
                    stroke={colors.primary}
                    strokeWidth={2}
                  />
                ) : null}
                {projected.map((p, i) => (
                  <Circle
                    key={i}
                    cx={p.x}
                    cy={p.y}
                    r={8}
                    fill={colors.primary}
                    fillOpacity={0.15}
                    stroke={colors.primary}
                    strokeWidth={2}
                  />
                ))}
              </Svg>
            ) : null}
          </Animated.View>
        </GestureDetector>

        {mapUrl && tileState === 'loading' ? (
          <View pointerEvents="none" style={styles.mapStatusOverlay}>
            <View style={styles.mapStatusCard}>
              <ActivityIndicator size="small" color={colors.primary} />
              <AgText variant="bodySmall" weight="semibold" style={styles.mapStatusText}>
                {t('farm.mapLoading')}
              </AgText>
            </View>
          </View>
        ) : null}

        {mapUrl && tileState === 'error' ? (
          <View style={styles.mapStatusOverlay}>
            <View style={styles.mapErrorCard}>
              <Map size={24} color={colors.primary} />
              <AgText variant="bodySmall" weight="semibold" style={styles.mapStatusText}>
                {t('farm.mapLoadFailed')}
              </AgText>
              <AgPressable
                accessibilityRole="button"
                accessibilityLabel={t('farm.retryMap')}
                onPress={() => setTileAttempt((attempt) => attempt + 1)}
                style={styles.mapRetryButton}
              >
                <RefreshCw size={17} color="#FFFFFF" />
                <AgText variant="bodySmall" weight="semibold" style={styles.mapRetryText}>
                  {t('farm.retryMap')}
                </AgText>
              </AgPressable>
            </View>
          </View>
        ) : null}

        {/* Zoom controls */}
        <View style={styles.zoomControls}>
          <ControlButton
            icon={<Plus size={20} color="#101713" />}
            onPress={() => changeZoom(1)}
            label={t('farm.zoomIn')}
          />
          <ControlButton
            icon={<Minus size={20} color="#101713" />}
            onPress={() => changeZoom(-1)}
            label={t('farm.zoomOut')}
          />
        </View>

        {/* Live area readout. `color="onPrimary"` is near-black -- correct
            for text sitting on the bright green `colors.primary` fill, but
            this badge's actual background is a translucent black pill
            (`areaReadout` below), so near-black-on-near-black made the area
            reading nearly unreadable, overlapping into the map's bottom-left
            corner (reported live 2026-08-17). Fixed to a fixed white, which
            reads correctly against the badge's own dark background
            regardless of theme. */}
        {areaHa > 0 ? <View style={styles.areaReadout}>
          <AgText variant="caption" weight="semibold" style={styles.areaReadoutText}>
            {`${areaHa.toFixed(2)} ${t('farm.hectaresShort')} · ${hectaresToAcres(areaHa).toFixed(2)} ${t('farm.acresShort')}`}
          </AgText>
        </View> : null}
      </View>

      <View style={styles.instructionRow}>
        <Info size={18} color={colors.textMuted} />
        <AgText variant="caption" style={styles.instructionText}>
          {t('farm.tapToDraw')}
        </AgText>
      </View>

      {/* Draw controls */}
      <View style={styles.drawControls}>
        <DrawAction
          icon={<Undo2 size={18} color="#101713" />}
          label={t('farm.undo')}
          onPress={undo}
          disabled={!vertices.length}
        />
        <DrawAction
          icon={<Trash2 size={18} color={colors.danger} />}
          label={t('farm.clear')}
          onPress={clear}
          disabled={!vertices.length}
        />
        <DrawAction
          icon={<Locate size={18} color={locating ? colors.textMuted : colors.primary} />}
          label={t('farm.useMyLocation')}
          onPress={() => void useGps()}
          disabled={locating}
        />
      </View>

      {locationError ? <AgText variant="bodySmall" color="danger" accessibilityRole="alert">
        {t(locationError === 'permission' ? 'farm.locationPermissionDenied' : 'farm.locationUnavailable')}
      </AgText> : null}
      {!isMapboxConfigured ? (
        <AgText variant="caption" className="mt-2" style={styles.fallbackText}>
          {t('farm.mapFallbackHint')}
        </AgText>
      ) : null}
    </View>
  );
}

function DrawAction({
  icon,
  label,
  onPress,
  primary,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  onPress: () => void;
  primary?: boolean;
  disabled?: boolean;
}) {
  return (
    <AgPressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={[styles.drawAction, primary && styles.drawActionPrimary, disabled && styles.disabled]}
    >
      {icon}
      <AgText
        variant="bodySmall"
        weight="semibold"
        color={primary ? 'onPrimary' : 'default'}
        style={styles.drawActionText}
      >
        {label}
      </AgText>
    </AgPressable>
  );
}

/** Neutral grid shown when no Mapbox token is configured. */
function GridBackdrop({ size, color }: { size: Size; color: string }) {
  const step = 32;
  const cols = Math.ceil(size.width / step);
  const rows = Math.ceil(size.height / step);
  return (
    <Svg width={size.width} height={size.height}>
      {Array.from({ length: cols }).map((_, i) => (
        <Line
          key={`c${i}`}
          x1={i * step}
          y1={0}
          x2={i * step}
          y2={size.height}
          stroke={color}
          strokeWidth={1}
        />
      ))}
      {Array.from({ length: rows }).map((_, i) => (
        <Line
          key={`r${i}`}
          x1={0}
          y1={i * step}
          x2={size.width}
          y2={i * step}
          stroke={color}
          strokeWidth={1}
        />
      ))}
    </Svg>
  );
}

const styles = StyleSheet.create({
  map: { overflow: 'hidden', borderRadius: 18, borderWidth: 1, borderColor: '#D9D6C8', backgroundColor: '#EAF3E5' },
  mapImage: { position: 'absolute', inset: 0, width: '100%', height: '100%' },
  mapStatusOverlay: { position: 'absolute', inset: 0, alignItems: 'center', justifyContent: 'center', padding: 24 },
  mapStatusCard: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 16, paddingVertical: 12, borderRadius: 14, borderWidth: 1, borderColor: '#C9D8C4', backgroundColor: 'rgba(255,255,255,0.94)' },
  mapErrorCard: { width: '100%', maxWidth: 280, alignItems: 'center', gap: 10, padding: 18, borderRadius: 16, borderWidth: 1, borderColor: '#C9D8C4', backgroundColor: 'rgba(255,255,255,0.97)' },
  mapStatusText: { color: '#183F2D', textAlign: 'center' },
  mapRetryButton: { minHeight: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingHorizontal: 18, borderRadius: 12, backgroundColor: '#176B36' },
  mapRetryText: { color: '#FFFFFF' },
  mapControl: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 14, borderWidth: 1, borderColor: '#D9D6C8', backgroundColor: '#FFFFFF' },
  zoomControls: { position: 'absolute', right: 12, top: 12, gap: 8 },
  areaReadout: { position: 'absolute', left: 12, bottom: 12, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 18, backgroundColor: 'rgba(0,0,0,0.68)' },
  areaReadoutText: { color: '#FFFFFF' },
  instructionRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 9, paddingHorizontal: 4, paddingTop: 12 },
  instructionText: { flex: 1, color: '#536158' },
  fallbackText: { color: '#536158' },
  drawControls: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  drawAction: { minWidth: 100, minHeight: 48, flexGrow: 1, flexBasis: 100, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, paddingHorizontal: 10, borderRadius: 13, borderWidth: 1, borderColor: '#D9D6C8', backgroundColor: '#FFFFFF' },
  drawActionPrimary: { borderColor: '#176B36', backgroundColor: '#EAF3E5' },
  drawActionText: { color: '#101713' },
  disabled: { opacity: 0.4 },
});
