import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { Alert, StyleSheet, View } from "react-native";

import { AgOfflineBanner, AgScreen } from "@/components/ui";

import { SoilFeatureHeader } from "../components/SoilFeatureHeader";
import { SoilReportForm } from "../components/SoilReportForm";
import { SOIL_SHADOW, SOIL_UI } from "../design";
import { useSubmitSoilReport } from "../hooks/useSoil";
import type { SoilReportInput } from "../types";

/** Upload a soil report (Soil Health Card values + optional photo). */
export function UploadSoilReportScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const submit = useSubmitSoilReport();

  const onSubmit = (input: SoilReportInput) => {
    submit.mutate(input, {
      onSuccess: (res) => {
        if (res.offline) Alert.alert(t("soil.savedOffline"));
        router.back();
      },
      onError: () => Alert.alert(t("soil.submitFailed")),
    });
  };

  return (
    <AgScreen scroll backgroundColor={SOIL_UI.canvas}>
      <AgOfflineBanner />
      <SoilFeatureHeader
        title={t("soil.uploadTitle")}
        subtitle={t("soil.uploadSubtitle")}
        onBack={() => router.back()}
      />
      <View style={styles.formCard}>
        <SoilReportForm
          farmId={farmId}
          submitting={submit.isPending}
          onSubmit={onSubmit}
        />
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  formCard: {
    marginTop: 16,
    padding: 16,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surface,
    ...SOIL_SHADOW,
  },
});
