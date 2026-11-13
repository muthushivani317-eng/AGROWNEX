import { Image } from "expo-image";
import { Camera, Images, Leaf, RefreshCw, ShieldAlert } from "lucide-react-native";
import { useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { useTranslation } from "react-i18next";
import { AgButton, AgCard, AgScreen, AgText } from "@/components/ui";
import type { PickedImage } from "@/features/disease/types";
import { captureFromCamera, pickFromGallery } from "@/features/disease/utils/pickDiseaseImage";
import { useAppTheme } from "@/hooks/useAppTheme";
import { GREEN_GRAM_PREDICTION_ENABLED, predictGreenGram, validateGreenGramUpload, type GreenGramClass, type GreenGramPredictionResponse } from "./greenGramApi";

const LABEL_KEYS: Record<GreenGramClass, string> = { healthy: "greenGram.diseases.healthy.name", leaf_curl: "greenGram.diseases.leafCurl.name", mymv: "greenGram.diseases.yellowMosaic.name" };
export function GreenGramUnavailableScreen({ initialImage = null, onChangeCrop }: { initialImage?: PickedImage | null; onChangeCrop?: () => void }) {
  const { t } = useTranslation(); const { colors } = useAppTheme();
  const [image, setImage] = useState<PickedImage | null>(initialImage); const [result, setResult] = useState<GreenGramPredictionResponse | null>(null); const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(false);
  const pick = async (source: "camera" | "gallery") => { const selected = source === "camera" ? await captureFromCamera({ base64: false }) : await pickFromGallery({ base64: false }); if (!selected) return; const invalid = validateGreenGramUpload(selected); if (invalid) { setError(t(`greenGram.errors.${invalid}`)); return; } setImage(selected); setResult(null); setError(null); };
  const analyze = async () => { if (!image || loading) return; setLoading(true); setError(null); setResult(null); try { setResult(await predictGreenGram(image)); } catch { setError(t(GREEN_GRAM_PREDICTION_ENABLED ? "greenGram.errors.retry" : "greenGram.errors.unavailable")); } finally { setLoading(false); } };
  const reset = () => { setImage(null); setResult(null); setError(null); };
  return <AgScreen scroll testID="green-gram-experimental-screen" contentContainerStyle={styles.screen}>
    <View style={styles.header}><Leaf size={30} color={colors.primary} /><View style={styles.flex}><AgText variant="headingM" weight="bold">{t("greenGram.title")}</AgText><AgText color="muted">{t("greenGram.subtitle")}</AgText></View></View>
    {onChangeCrop ? <AgButton title={t("greenGram.changeCrop")} variant="outline" onPress={onChangeCrop} /> : null}
    <AgCard style={styles.warning}><ShieldAlert size={22} color={colors.warning} /><AgText style={styles.flex} weight="bold">{t("greenGram.experimental")}</AgText></AgCard>
    {image ? <View style={styles.gap}><Image source={{ uri: image.uri }} style={styles.preview} contentFit="cover" accessibilityLabel={t("greenGram.selectedImage")} /><AgButton title={t("greenGram.replaceImage")} variant="outline" onPress={reset} leftIcon={<RefreshCw size={19} color={colors.primary} />} /></View> : <AgCard style={styles.gap}><AgText weight="bold">{t("greenGram.introTitle")}</AgText><AgText color="muted">{t("greenGram.introBody")}</AgText><AgButton title={t("greenGram.camera")} onPress={() => void pick("camera")} leftIcon={<Camera size={20} color={colors.onPrimary} />} /><AgButton title={t("greenGram.gallery")} variant="outline" onPress={() => void pick("gallery")} leftIcon={<Images size={20} color={colors.primary} />} /></AgCard>}
    {error ? <AgCard testID="green-gram-error"><AgText color="danger">{error}</AgText></AgCard> : null}
    {image && !result ? <AgButton title={loading ? t("greenGram.analyzing") : t("greenGram.analyze")} loading={loading} disabled={loading || !GREEN_GRAM_PREDICTION_ENABLED} onPress={() => void analyze()} /> : null}
    {loading ? <View style={styles.loading} accessibilityRole="progressbar"><ActivityIndicator color={colors.primary} /><AgText>{t("greenGram.analyzing")}</AgText></View> : null}
    {result ? <AgCard style={styles.gap} testID="green-gram-result"><AgText variant="headingS" weight="bold">{t("greenGram.resultTitle")}</AgText><AgText weight="bold" color="primary">{t(LABEL_KEYS[result.predicted_class])}</AgText><AgText>{t("greenGram.confidenceLabel")}: {(result.confidence * 100).toFixed(1)}%</AgText><AgText weight="bold">{t("greenGram.topPredictions")}</AgText>{result.top_three_predictions.map((item) => <View key={item.class_id} style={styles.rank}><AgText>{t(LABEL_KEYS[item.class_id])}</AgText><AgText>{(item.confidence * 100).toFixed(1)}%</AgText></View>)}<AgText color="muted">{t("greenGram.reviewRequired")}</AgText><AgText variant="caption">{result.model_version}</AgText><AgButton title={t("greenGram.retry")} variant="secondary" onPress={reset} /></AgCard> : null}
  </AgScreen>;
}
const styles = StyleSheet.create({ screen: { paddingBottom: 36, gap: 16 }, header: { flexDirection: "row", alignItems: "center", gap: 12 }, flex: { flex: 1 }, warning: { flexDirection: "row", gap: 10, alignItems: "flex-start" }, gap: { gap: 12 }, preview: { width: "100%", aspectRatio: 1, borderRadius: 18 }, loading: { flexDirection: "row", gap: 8, alignItems: "center" }, rank: { flexDirection: "row", justifyContent: "space-between", gap: 12 } });
