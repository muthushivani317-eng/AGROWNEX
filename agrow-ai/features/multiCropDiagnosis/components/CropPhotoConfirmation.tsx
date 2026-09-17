import { CheckCircle2, RefreshCw, ShieldCheck } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { cropConfirmationCopy } from "../cropConfirmationCopy";

export function CropPhotoConfirmation(props: {
  cropId: string;
  cropName?: string;
  suggestedCropId?: string | null;
  suggestedCropName?: string | null;
  identificationConfidence?: number | null;
  confirmed: boolean;
  onConfirm: () => void;
  onChangeCrop?: () => void;
  onRetake?: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const cropName = props.cropName ?? props.cropId;
  const copy = cropConfirmationCopy({
    cropId: props.cropId,
    cropName,
    suggestedCropId: props.suggestedCropId,
    suggestedCropName: props.suggestedCropName,
    identificationConfidence: props.identificationConfidence,
  });
  const explanation = props.confirmed
    ? t(copy.key, copy.params)
    : t("disease.confirmationNotice");

  return (
    <View
      testID="crop-photo-confirmation"
      style={[
        styles.card,
        { backgroundColor: colors.card, borderColor: colors.border },
      ]}
    >
      <View style={styles.headingRow}>
        <View
          style={[styles.iconTile, { backgroundColor: `${colors.primary}16` }]}
        >
          <ShieldCheck size={25} color={colors.primaryLight} />
        </View>
        <View style={styles.copy}>
          <AgText variant="bodyLarge" weight="semibold">
            {t("disease.cropConfirmQuestion", { crop: cropName })}
          </AgText>
          <AgText variant="bodySmall" color="muted">
            {explanation}
          </AgText>
        </View>
      </View>

      <Pressable
        onPress={props.onConfirm}
        disabled={props.confirmed}
        accessibilityRole="button"
        accessibilityState={{
          disabled: props.confirmed,
          checked: props.confirmed,
        }}
        accessibilityLabel={
          props.confirmed
            ? t("disease.cropConfirmed", { crop: cropName })
            : t("disease.confirmCrop", { crop: cropName })
        }
        style={({ pressed }) => [
          styles.confirmButton,
          {
            backgroundColor: props.confirmed
              ? colors.primaryDark
              : colors.primary,
            opacity: pressed ? 0.78 : 1,
          },
        ]}
      >
        <CheckCircle2 size={20} color={colors.onPrimary} />
        <AgText
          variant="body"
          weight="semibold"
          color="onPrimary"
          style={styles.buttonText}
        >
          {props.confirmed
            ? t("disease.cropConfirmed", { crop: cropName })
            : t("disease.confirmCrop", { crop: cropName })}
        </AgText>
      </Pressable>

      {props.onChangeCrop ? (
        <Pressable
          onPress={props.onChangeCrop}
          accessibilityRole="button"
          accessibilityLabel={t("banana.ui.changeCrop")}
          style={({ pressed }) => [
            styles.secondaryButton,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: pressed ? 0.72 : 1,
            },
          ]}
        >
          <AgText variant="body" weight="semibold">
            {t("banana.ui.changeCrop")}
          </AgText>
        </Pressable>
      ) : null}

      {props.onRetake ? (
        <Pressable
          onPress={props.onRetake}
          accessibilityRole="button"
          accessibilityLabel={t("disease.retakePhoto")}
          style={({ pressed }) => [
            styles.retake,
            { opacity: pressed ? 0.65 : 1 },
          ]}
        >
          <RefreshCw size={18} color={colors.primaryLight} />
          <AgText variant="bodySmall" weight="semibold" color="primary">
            {t("disease.retakePhoto")}
          </AgText>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 22,
    padding: 16,
    gap: 12,
    marginTop: 16,
  },
  headingRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  iconTile: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  copy: { flex: 1, gap: 5 },
  confirmButton: {
    minHeight: 52,
    borderRadius: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    paddingHorizontal: 16,
  },
  buttonText: { flexShrink: 1, textAlign: "center" },
  secondaryButton: {
    minHeight: 50,
    borderWidth: 1,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  retake: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
});
