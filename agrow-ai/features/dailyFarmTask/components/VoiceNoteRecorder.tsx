// Voice note recording step of the task-response flow. Hard-capped at 10
// seconds -- kept short deliberately so it's lightweight to record, upload
// over poor connectivity, and quick for an FPO/agronomist to review.
//
// Uses `expo-audio` (the current Expo SDK 57 recording API -- the older
// `expo-av` Audio.Recording API this was originally prototyped against is
// deprecated on this SDK). `expo-audio` was not previously a dependency of
// this app; it was added alongside this feature (see package.json) because
// no other screen records audio today. Needs a native rebuild (a new dev
// client / EAS build) before this ships -- see the integration report.
import {
  AudioQuality,
  IOSOutputFormat,
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import type { RecordingOptions } from "expo-audio";
import { Mic, Square } from "lucide-react-native";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";

import { AgButton, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { MAX_VOICE_NOTE_SECONDS } from "../constants";
import { useUploadTaskVoiceNote } from "../hooks/useDailyTask";

export const GROUNDNUT_SPEECH_RECORDING_OPTIONS: RecordingOptions = {
  extension: ".amr",
  sampleRate: 16_000,
  numberOfChannels: 1,
  bitRate: 12_200,
  android: { outputFormat: "amrnb", audioEncoder: "amr_nb" },
  ios: { outputFormat: IOSOutputFormat.AMR, audioQuality: AudioQuality.MEDIUM },
  web: { mimeType: "audio/webm", bitsPerSecond: 64_000 },
};

interface Props {
  taskId?: string;
  onDone?: () => void;
  onSkip?: () => void;
  onRecorded?: (uri: string) => Promise<void>;
  recordingOptions?: RecordingOptions;
  labels?: {
    title: string;
    start: string;
    stop: string;
    error: string;
  };
}

export function VoiceNoteRecorder({
  taskId,
  onDone,
  onSkip,
  onRecorded,
  recordingOptions = RecordingPresets.HIGH_QUALITY,
  labels,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const recorder = useAudioRecorder(recordingOptions);
  const state = useAudioRecorderState(recorder, 200);
  const [error, setError] = useState<string | null>(null);
  const upload = useUploadTaskVoiceNote(taskId ?? "");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (state.isRecording && state.durationMillis / 1000 >= MAX_VOICE_NOTE_SECONDS) {
      void stop();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.isRecording, state.durationMillis]);

  const start = async () => {
    setError(null);
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) {
      setError(t("dailyTask.voicePermissionDenied"));
      return;
    }
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
    recorder.record();
  };

  const stop = async () => {
    if (!state.isRecording) return;
    await recorder.stop();
    const uri = recorder.uri;
    if (!uri) return;
    const durationSeconds = Math.round(state.durationMillis / 1000);
    try {
      setProcessing(true);
      if (onRecorded) await onRecorded(uri);
      else if (taskId) await upload.mutateAsync({ fileUri: uri, durationSeconds });
    } catch {
      setError(labels?.error ?? t("dailyTask.voiceUploadFailed"));
    } finally {
      setProcessing(false);
    }
  };

  const seconds = Math.min(MAX_VOICE_NOTE_SECONDS, Math.floor(state.durationMillis / 1000));

  return (
    <View style={styles.container}>
      <AgText variant="body" weight="semibold" center style={styles.title}>
        {labels?.title ?? t("dailyTask.recordVoiceNote")}
      </AgText>

      <Pressable
        onPress={state.isRecording ? stop : start}
        style={[
          styles.recordButton,
          { backgroundColor: state.isRecording ? colors.danger : colors.primary },
        ]}
        accessibilityRole="button"
        accessibilityLabel={
          state.isRecording
            ? (labels?.stop ?? t("dailyTask.voiceStop"))
            : (labels?.start ?? t("dailyTask.recordVoiceNote"))
        }
      >
        {state.isRecording ? (
          <Square size={30} color={colors.onPrimary} />
        ) : (
          <Mic size={30} color={colors.onPrimary} />
        )}
      </Pressable>

      {state.isRecording ? (
        <AgText variant="bodyLarge" weight="semibold" style={styles.timer}>
          {seconds}s / {MAX_VOICE_NOTE_SECONDS}s
        </AgText>
      ) : null}
      {upload.isPending || processing ? <ActivityIndicator style={styles.spinner} /> : null}
      {error ? (
        <AgText variant="bodySmall" center style={{ color: colors.danger, marginTop: 8 }}>
          {error}
        </AgText>
      ) : null}

      <View style={styles.footerRow}>
        {onDone && !state.isRecording && !upload.isPending && !processing ? (
          <AgButton title={t("dailyTask.voiceDone")} onPress={onDone} size="sm" />
        ) : null}
        {onSkip ? (
          <AgButton title={t("dailyTask.voiceSkip")} onPress={onSkip} variant="ghost" size="sm" />
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", paddingVertical: 8 },
  title: { marginBottom: 16 },
  recordButton: { width: 80, height: 80, borderRadius: 40, alignItems: "center", justifyContent: "center" },
  timer: { marginTop: 12 },
  spinner: { marginTop: 12 },
  footerRow: { flexDirection: "row", gap: 16, marginTop: 20 },
});
