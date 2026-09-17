import { ImagePlus, X } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  View,
} from "react-native";

import {
  AgButton,
  AgCard,
  AgDropdown,
  AgInput,
  AgPressable,
  AgText,
} from "@/components/ui";
import { uploadService } from "@/features/profile/services/uploadProvider";
import { useAppTheme } from "@/hooks/useAppTheme";
import { capturePhoto, pickPhoto } from "@/utils/image";

import {
  DRAINAGE_LABEL_KEY,
  DRAINAGE_OPTIONS,
  PARAMETER_LABEL_KEY,
  SOURCE_LABEL_KEY,
  SOURCES,
} from "../constants";
import type { DrainageClass, SoilReportInput, SoilSource } from "../types";
import { SOIL_UI } from "../design";

interface Props {
  farmId: string;
  submitting: boolean;
  onSubmit: (input: SoilReportInput) => void;
}

const NUMERIC_FIELDS = [
  "ph",
  "organic_carbon",
  "nitrogen",
  "phosphorus",
  "potassium",
  "ec_salinity",
  "water_holding_capacity",
] as const;

type NumericField = (typeof NUMERIC_FIELDS)[number];

const FIELD_TO_INPUT: Record<NumericField, keyof SoilReportInput["values"]> = {
  ph: "ph",
  organic_carbon: "organicCarbon",
  nitrogen: "nitrogen",
  phosphorus: "phosphorus",
  potassium: "potassium",
  ec_salinity: "ecSalinity",
  water_holding_capacity: "waterHoldingCapacity",
};

/** Upload a soil report: values from a Soil Health Card + optional photo. */
export function SoilReportForm({ farmId, submitting, onSubmit }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  const [source, setSource] = useState<SoilSource>("soil_health_card");
  const [testDate, setTestDate] = useState("");
  const [drainage, setDrainage] = useState<DrainageClass | "">("");
  const [raw, setRaw] = useState<Record<NumericField, string>>({
    ph: "",
    organic_carbon: "",
    nitrogen: "",
    phosphorus: "",
    potassium: "",
    ec_salinity: "",
    water_holding_capacity: "",
  });
  const [photo, setPhoto] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadPhoto = async (pick: () => Promise<string | null>) => {
    const uri = await pick();
    if (!uri) return;
    setUploading(true);
    try {
      setPhoto(await uploadService.uploadImage(uri, "soil"));
    } catch {
      Alert.alert(t("soil.uploadFailed"));
    } finally {
      setUploading(false);
    }
  };

  // Offers both camera and gallery -- previously only the gallery was
  // reachable here (2026-08 pre-release audit).
  const addPhoto = () => {
    Alert.alert(t("soil.reportPhoto"), undefined, [
      {
        text: t("soil.takePhoto"),
        onPress: () => void uploadPhoto(capturePhoto),
      },
      {
        text: t("soil.chooseGallery"),
        onPress: () => void uploadPhoto(pickPhoto),
      },
      { text: t("common.cancel"), style: "cancel" },
    ]);
  };

  const submit = () => {
    const values: SoilReportInput["values"] = {};
    let hasValue = false;
    for (const field of NUMERIC_FIELDS) {
      const parsed = parseFloat(raw[field]);
      if (!Number.isNaN(parsed)) {
        (values as Record<string, number>)[FIELD_TO_INPUT[field]] = parsed;
        hasValue = true;
      }
    }
    if (drainage) values.drainage = drainage;
    if (!hasValue && !photo) {
      setError(t("soil.errorNoValues"));
      return;
    }
    setError(null);
    onSubmit({
      farmId,
      source,
      reportUrl: photo,
      testDate: /^\d{4}-\d{2}-\d{2}$/.test(testDate) ? testDate : null,
      values,
    });
  };

  return (
    <View style={styles.form}>
      <View style={styles.sectionLabel}>
        <AgText
          variant="label"
          weight="semibold"
          style={styles.sectionLabelText}
        >
          {t("soil.source")}
        </AgText>
      </View>
      <AgDropdown
        label={t("soil.source")}
        placeholder={t("soil.source")}
        value={source}
        options={SOURCES.map((s) => ({
          value: s,
          label: t(SOURCE_LABEL_KEY[s]),
        }))}
        onChange={(v) => setSource(v as SoilSource)}
      />
      <AgInput
        label={t("soil.testDate")}
        placeholder="YYYY-MM-DD"
        value={testDate}
        onChangeText={setTestDate}
      />

      <View style={styles.sectionLabel}>
        <AgText
          variant="label"
          weight="semibold"
          style={styles.sectionLabelText}
        >
          {t("soil.values")}
        </AgText>
        <AgText variant="caption" style={styles.helperText}>
          {t("soil.optional")}
        </AgText>
      </View>
      {NUMERIC_FIELDS.map((field) => (
        <AgInput
          key={field}
          label={t(PARAMETER_LABEL_KEY[field])}
          placeholder={t("soil.optional")}
          keyboardType="numeric"
          value={raw[field]}
          onChangeText={(text) =>
            setRaw((prev) => ({ ...prev, [field]: text }))
          }
        />
      ))}
      <AgDropdown
        label={t("soil.paramDrainage")}
        placeholder={t("soil.optional")}
        value={drainage}
        options={[
          { value: "", label: t("soil.optional") },
          ...DRAINAGE_OPTIONS.map((d) => ({
            value: d,
            label: t(DRAINAGE_LABEL_KEY[d]),
          })),
        ]}
        onChange={(v) => setDrainage(v as DrainageClass | "")}
      />

      {/* Optional report photo */}
      <View style={styles.photoSection}>
        <AgText
          variant="label"
          weight="semibold"
          style={styles.sectionLabelText}
        >
          {t("soil.reportPhoto")}
        </AgText>
        <View style={styles.photoRow}>
          {photo ? (
            <View style={styles.photoPreview}>
              <Image
                source={{ uri: photo }}
                style={styles.photoImage}
                resizeMode="cover"
              />
              <Pressable
                onPress={() => setPhoto(null)}
                accessibilityRole="button"
                accessibilityLabel={t("common.delete")}
                className="absolute -right-1.5 -top-1.5 h-6 w-6 items-center justify-center rounded-full bg-danger"
              >
                <X size={14} color="#fff" />
              </Pressable>
            </View>
          ) : (
            <AgPressable
              onPress={addPhoto}
              disabled={uploading}
              accessibilityRole="button"
              accessibilityLabel={t("soil.addPhoto")}
              style={styles.photoPicker}
            >
              {uploading ? (
                <ActivityIndicator color={colors.primary} />
              ) : (
                <ImagePlus size={22} color={colors.primary} />
              )}
            </AgPressable>
          )}
        </View>
        <AgText variant="caption" color="muted">
          {t("soil.privacyNote")}
        </AgText>
      </View>

      {error ? (
        <AgCard className="border border-danger/40 bg-danger/5">
          <AgText variant="bodySmall" className="text-danger">
            {error}
          </AgText>
        </AgCard>
      ) : null}

      <AgButton
        title={t("soil.submit")}
        variant="primary"
        onPress={submit}
        loading={submitting}
        disabled={uploading}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: 16 },
  sectionLabel: {
    paddingTop: 4,
    paddingBottom: 2,
    borderBottomWidth: 1,
    borderBottomColor: SOIL_UI.border,
    gap: 2,
  },
  sectionLabelText: { color: SOIL_UI.text },
  helperText: { color: SOIL_UI.muted },
  photoSection: {
    gap: 10,
    padding: 14,
    borderRadius: 18,
    backgroundColor: SOIL_UI.surfaceSoft,
  },
  photoRow: { flexDirection: "row", gap: 10 },
  photoPreview: { width: 88, height: 88 },
  photoImage: { width: 88, height: 88, borderRadius: 14 },
  photoPicker: {
    width: 88,
    height: 88,
    borderRadius: 14,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: SOIL_UI.green,
    backgroundColor: SOIL_UI.surface,
    alignItems: "center",
    justifyContent: "center",
  },
});
