import { ImageOff, RefreshCw, Satellite } from "lucide-react-native";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import { AgBadge, AgText } from "@/components/ui";

import type { SatelliteImage, SatelliteSession } from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

/** The latest scene preview. Shows the true-colour/NDVI image when the provider
 * supplied one; otherwise an honest "no imagery preview" (never fabricated). */
export function LatestImageCard({
  session,
  onOpen,
  onRepair,
  repairing = false,
}: {
  session: SatelliteSession;
  onOpen: (image: SatelliteImage) => void;
  onRepair?: () => void;
  repairing?: boolean;
}) {
  const { t } = useTranslation();
  const layerLabels: Record<string, string> = {
    true_color: "True colour", ndvi: "Vegetation", ndre: "Chlorophyll",
    ndmi: "Moisture", crop_stress: "Crop stress", bare_cover: "Bare soil / cover",
    surface_water: "Surface water",
  };
  const [selectedBand, setSelectedBand] = useState("true_color");
  const [selectedZone, setSelectedZone] = useState<Record<string, unknown> | null>(null);
  const preview = session.images.find((i) => i.band === selectedBand) ?? session.images[0] ?? null;
  const zones = Array.isArray(session.metadata?.spatial_variability_zones)
    ? (session.metadata!.spatial_variability_zones as Record<string, unknown>[])
    : [];
  const previewUrl = preview?.imageUrl ?? preview?.thumbnailUrl ?? null;
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(Boolean(previewUrl));
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    setFailed(false);
    setLoading(Boolean(previewUrl));
  }, [previewUrl, session]);

  const retry = () => {
    if (onRepair) {
      onRepair();
      return;
    }
    setFailed(false);
    setLoading(true);
    setRetryKey((value) => value + 1);
  };

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Satellite size={16} color={SATELLITE_UI.spectral} />
          <AgText variant="label" weight="semibold" style={styles.mutedText}>
            {t("satellite.latestImage")}
          </AgText>
        </View>
        <AgBadge light label={session.provider.toUpperCase()} tone="info" />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.layers}>
        {session.images.map((image) => (
          <Pressable
            key={image.id}
            onPress={() => { setSelectedBand(image.band); setSelectedZone(null); }}
            style={[styles.layerChip, selectedBand === image.band && styles.layerChipActive]}
            accessibilityRole="button"
          >
            <AgText variant="caption" weight="semibold" style={selectedBand === image.band ? styles.layerTextActive : styles.layerText}>
              {layerLabels[image.band] ?? image.band.replaceAll("_", " ")}
            </AgText>
          </Pressable>
        ))}
      </ScrollView>

      {preview && previewUrl && !failed ? (
        <Pressable
          onPress={() => onOpen(preview)}
          accessibilityRole="imagebutton"
          accessibilityLabel={t("satellite.viewImage")}
        >
          <Image
            key={`${previewUrl}-${retryKey}`}
            source={{ uri: previewUrl }}
            style={styles.image}
            resizeMode="cover"
            onLoadStart={() => setLoading(true)}
            onLoadEnd={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setFailed(true);
            }}
          />
          {zones.map((zone, index) => {
            const position = (zone.relative_position ?? {}) as Record<string, unknown>;
            const x = Number(position.x ?? 50);
            const y = Number(position.y ?? 50);
            const weak = ["inspect_first", "irrigate_first"].includes(String(zone.priority));
            return (
              <Pressable
                key={String(zone.zone_id ?? index)}
                onPress={() => setSelectedZone(zone)}
                accessibilityLabel={`Inspect ${String(zone.zone_id ?? `zone ${index + 1}`)}`}
                style={[styles.zoneDot, { left: `${Math.max(4, Math.min(92, x))}%`, top: `${Math.max(4, Math.min(88, y))}%` }, weak && styles.zoneDotWeak]}
              />
            );
          })}
          {loading ? (
            <View style={styles.loadingOverlay} pointerEvents="none">
              <ActivityIndicator size="large" color={SATELLITE_UI.spectral} />
              <AgText variant="bodySmall" style={styles.statusText}>
                {t("satellite.imageLoading")}
              </AgText>
            </View>
          ) : null}
        </Pressable>
      ) : (
        <View style={styles.emptyImage}>
          <ImageOff size={28} color={SATELLITE_UI.muted} />
          <AgText
            variant="bodySmall"
            style={styles.mutedText}
            className="px-6 text-center"
          >
            {failed
              ? t("satellite.imageLoadFailed")
              : t("satellite.noImagePreview")}
          </AgText>
          {failed ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t("common.retry")}
              onPress={retry}
              disabled={repairing}
              style={styles.retryButton}
            >
              {repairing ? (
                <ActivityIndicator size="small" color={SATELLITE_UI.text} />
              ) : (
                <RefreshCw size={17} color={SATELLITE_UI.text} />
              )}
              <AgText variant="label" weight="semibold" style={styles.retryText}>
                {t("common.retry")}
              </AgText>
            </Pressable>
          ) : null}
        </View>
      )}
      {selectedZone ? (
        <View style={styles.zonePanel}>
          <AgText variant="label" weight="semibold" style={styles.primaryText}>
            {String(selectedZone.zone_id ?? "Selected zone")}
          </AgText>
          <AgText variant="bodySmall" style={styles.mutedText}>
            NDVI {formatValue(selectedZone.ndvi)} · NDMI {formatValue(selectedZone.ndmi)} · NDRE {formatValue(selectedZone.ndre)}
          </AgText>
          <AgText variant="bodySmall" style={styles.primaryText}>
            {friendlyAction(String(selectedZone.suggested_action ?? selectedZone.priority ?? "Recheck after the next scan"))}
          </AgText>
          <AgText variant="caption" style={styles.mutedText}>
            Confidence {String(selectedZone.confidence ?? session.confidence)}%
            {selectedZone.persistent ? " · Persistent weak zone" : ""}
          </AgText>
        </View>
      ) : zones.length > 0 ? (
        <AgText variant="caption" style={styles.mutedText}>Tap a marker to inspect that part of the field.</AgText>
      ) : null}
    </View>
  );
}

function formatValue(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : "—";
}

function friendlyAction(value: string) {
  return value.replaceAll("_", " ").replaceAll(":", " · ").replace(/^./, (c) => c.toUpperCase());
}

const styles = StyleSheet.create({
  card: {
    gap: 12,
    padding: 14,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: SATELLITE_UI.border,
    backgroundColor: SATELLITE_UI.surface,
    ...SATELLITE_SHADOW,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  titleRow: { flex: 1, flexDirection: "row", alignItems: "center", gap: 8 },
  layers: { gap: 8, paddingRight: 8 },
  layerChip: { paddingHorizontal: 12, minHeight: 38, justifyContent: "center", borderRadius: 19, borderWidth: 1, borderColor: SATELLITE_UI.border, backgroundColor: SATELLITE_UI.surfaceSoft },
  layerChipActive: { backgroundColor: SATELLITE_UI.spectral, borderColor: SATELLITE_UI.spectral },
  layerText: { color: SATELLITE_UI.text },
  layerTextActive: { color: SATELLITE_UI.white },
  image: {
    width: "100%",
    height: 224,
    borderRadius: 18,
    backgroundColor: SATELLITE_UI.orbit,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFill,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    backgroundColor: SATELLITE_UI.orbit,
  },
  emptyImage: {
    height: 190,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: SATELLITE_UI.surfaceSoft,
  },
  mutedText: { color: SATELLITE_UI.muted },
  statusText: { color: SATELLITE_UI.white },
  retryButton: {
    minHeight: 44,
    paddingHorizontal: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: SATELLITE_UI.border,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: SATELLITE_UI.surface,
  },
  retryText: { color: SATELLITE_UI.text },
  zoneDot: { position: "absolute", width: 24, height: 24, marginLeft: -12, marginTop: -12, borderRadius: 12, borderWidth: 3, borderColor: SATELLITE_UI.white, backgroundColor: SATELLITE_UI.spectral },
  zoneDotWeak: { backgroundColor: "#F4B62A" },
  zonePanel: { gap: 5, padding: 14, borderRadius: 16, borderWidth: 1, borderColor: SATELLITE_UI.border, backgroundColor: SATELLITE_UI.surfaceSoft },
  primaryText: { color: SATELLITE_UI.text },
});
