// Photo upload step of the task-response flow. Reuses `expo-image-picker`,
// already a real dependency and the same pattern used elsewhere in the app
// (e.g. Disease Detection photo capture) -- no new camera/permission
// handling invented for this feature.
import * as ImagePicker from "expo-image-picker";
import { Camera, ImageIcon } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Image, Pressable, StyleSheet, View } from "react-native";

import { AgButton, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { useUploadTaskPhoto } from "../hooks/useDailyTask";

interface Props {
  taskId: string;
  onDone: () => void;
  onSkip: () => void;
}

export function PhotoUploadFlow({ taskId, onDone, onSkip }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [uri, setUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const upload = useUploadTaskPhoto(taskId);

  const pickAndUpload = async (source: "camera" | "library") => {
    const permission =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(t("dailyTask.photoPermissionDenied"));
      return;
    }
    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync({ quality: 0.6 })
        : await ImagePicker.launchImageLibraryAsync({ quality: 0.6 });
    if (result.canceled) return;

    const pickedUri = result.assets[0].uri;
    setUri(pickedUri);
    setError(null);
    try {
      // The shared apiClient interceptor already retries transient failures
      // (docs/FRONTEND_ARCHITECTURE.md → API LAYER); this component only
      // shows optimistic local state, it doesn't implement its own
      // retry/backoff or offline queue.
      await upload.mutateAsync(pickedUri);
    } catch {
      setError(t("dailyTask.photoUploadFailed"));
    }
  };

  return (
    <View style={styles.container}>
      <AgText variant="body" weight="semibold" center style={styles.title}>
        {t("dailyTask.addPhoto")}
      </AgText>

      {uri ? (
        <Image source={{ uri }} style={styles.preview} />
      ) : (
        <View style={styles.pickRow}>
          <Pressable
            onPress={() => pickAndUpload("camera")}
            style={[styles.pickButton, { backgroundColor: colors.primary }]}
            accessibilityRole="button"
          >
            <Camera size={26} color={colors.onPrimary} />
          </Pressable>
          <Pressable
            onPress={() => pickAndUpload("library")}
            style={[styles.pickButton, { backgroundColor: colors.textMuted }]}
            accessibilityRole="button"
          >
            <ImageIcon size={26} color={colors.onPrimary} />
          </Pressable>
        </View>
      )}

      {upload.isPending ? <ActivityIndicator style={styles.spinner} /> : null}
      {error ? (
        <AgText variant="bodySmall" center style={{ color: colors.danger, marginBottom: 8 }}>
          {error}
        </AgText>
      ) : null}

      <View style={styles.footerRow}>
        {uri && !upload.isPending ? (
          <AgButton title={t("dailyTask.photoContinue")} onPress={onDone} size="sm" />
        ) : null}
        <AgButton title={t("dailyTask.photoSkip")} onPress={onSkip} variant="ghost" size="sm" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", paddingVertical: 8 },
  title: { marginBottom: 16 },
  preview: { width: 160, height: 160, borderRadius: 16, marginBottom: 16 },
  pickRow: { flexDirection: "row", gap: 16, marginBottom: 16 },
  pickButton: { alignItems: "center", justifyContent: "center", width: 64, height: 64, borderRadius: 16 },
  spinner: { marginBottom: 8 },
  footerRow: { flexDirection: "row", gap: 16, marginTop: 4 },
});
