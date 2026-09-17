import { Activity, CloudSun, Radar, Sprout } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";
import type { SatelliteSession } from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

type Json = Record<string, unknown>;

export function SatelliteAnalysisCard({ session }: { session: SatelliteSession }) {
  const metadata = (session.metadata ?? {}) as Json;
  const quality = (metadata.data_quality ?? {}) as Json;
  const stage = (metadata.crop_stage_interpretation ?? {}) as Json;
  const canopy = (metadata.canopy ?? {}) as Json;
  const priorities = (metadata.priority_zones ?? {}) as Json;
  const persistent = Array.isArray(metadata.persistent_weak_zone_ids)
    ? metadata.persistent_weak_zone_ids.length : 0;

  return (
    <View style={styles.card}>
      <AgText variant="headingL" weight="semibold" style={styles.title}>Field interpretation</AgText>
      <Row icon={<CloudSun size={20} color={SATELLITE_UI.spectral} />} title="Data quality"
        text={`${value(quality.valid_field_coverage_pct)}% usable coverage · ${value(quality.cloud_shadow_pct)}% cloud/shadow · ${value(quality.spatial_resolution_m)} m resolution · ${value(quality.scene_age_days)} days old`} />
      <Row icon={<Sprout size={20} color={SATELLITE_UI.spectral} />} title="Crop stage and canopy"
        text={`${friendly(stage.stage)}${stage.days_after_sowing != null ? ` · day ${stage.days_after_sowing}` : ""} · estimated cover ${value(canopy.estimated_cover_pct)}% · ${friendly(canopy.emergence_uniformity)}`} />
      <Row icon={<Activity size={20} color={SATELLITE_UI.spectral} />} title="Field priorities"
        text={`${count(priorities.inspect_first)} inspect first · ${count(priorities.irrigate_first)} irrigate first · ${count(priorities.healthy)} healthy · ${persistent} persistent weak`} />
      <Row icon={<Radar size={20} color={SATELLITE_UI.spectral} />} title="Cloud-independent radar"
        text="Sentinel-1 surface-water evidence is included in the Waterlogging & flood check when a usable radar scene is available." />
      <AgText variant="caption" style={styles.note}>Satellite results are screening estimates, not laboratory measurements or proof of crop damage.</AgText>
    </View>
  );
}

function Row({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <View style={styles.row}><View style={styles.icon}>{icon}</View><View style={styles.copy}><AgText variant="label" weight="semibold" style={styles.title}>{title}</AgText><AgText variant="bodySmall" style={styles.body}>{text}</AgText></View></View>;
}
function value(input: unknown) { return input == null || input === "" ? "—" : String(input); }
function friendly(input: unknown) { const text = value(input); return text.replaceAll("_", " ").replace(/^./, c => c.toUpperCase()); }
function count(input: unknown) { return Array.isArray(input) ? input.length : 0; }

const styles = StyleSheet.create({
  card: { gap: 14, padding: 18, borderRadius: 24, borderWidth: 1, borderColor: SATELLITE_UI.border, backgroundColor: SATELLITE_UI.surface, ...SATELLITE_SHADOW },
  row: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  icon: { width: 42, height: 42, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: SATELLITE_UI.surfaceSoft },
  copy: { flex: 1, gap: 3 }, title: { color: SATELLITE_UI.text }, body: { color: SATELLITE_UI.muted }, note: { color: SATELLITE_UI.muted },
});
