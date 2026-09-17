// Task response action sheet. Exactly four buttons, same order, same
// wording, for every task type -- this component is the ONLY place those
// four buttons are rendered, so the ordering/wording requirement is
// enforced by construction, not by convention across screens (integration
// brief: "preserve the single shared response-button component").
import { CircleCheckBig, CircleX, PhoneCall, TriangleAlert } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Modal, Pressable, StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { useRespondToTask } from "../hooks/useDailyTask";
import type { ResponseType, TaskCard, TaskRespondResponse } from "../types";
import { PhotoUploadFlow } from "./PhotoUploadFlow";
import { VoiceNoteRecorder } from "./VoiceNoteRecorder";

interface Props {
  visible: boolean;
  task: TaskCard;
  onClose: () => void;
  onResponded: (result: TaskRespondResponse) => void;
}

type MediaStep = "none" | "photo" | "voice";

export function TaskResponseSheet({ visible, task, onClose, onResponded }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const respond = useRespondToTask(task.id);
  const [mediaStep, setMediaStep] = useState<MediaStep>("none");
  const [submittingType, setSubmittingType] = useState<ResponseType | null>(null);

  const BUTTONS: {
    type: ResponseType;
    label: string;
    icon: typeof CircleCheckBig;
    tone: string;
  }[] = [
    { type: "done", label: t("dailyTask.buttonDone"), icon: CircleCheckBig, tone: colors.primary },
    { type: "problem_found", label: t("dailyTask.buttonProblemFound"), icon: TriangleAlert, tone: colors.warning },
    { type: "no_issue", label: t("dailyTask.buttonNoIssue"), icon: CircleX, tone: colors.textMuted },
    { type: "need_help", label: t("dailyTask.buttonNeedHelp"), icon: PhoneCall, tone: colors.danger },
  ];

  const submit = async (type: ResponseType) => {
    setSubmittingType(type);
    try {
      const result = await respond.mutateAsync({ response_type: type });
      onResponded(result);
      if (result.follow_up_prompt !== "none" && (task.can_upload_photo || task.can_record_voice_note)) {
        setMediaStep(task.can_upload_photo ? "photo" : "voice");
      } else {
        onClose();
      }
    } finally {
      setSubmittingType(null);
    }
  };

  const handleClose = () => {
    setMediaStep("none");
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={handleClose}>
      <View style={styles.backdrop}>
        <View style={[styles.sheet, { backgroundColor: colors.card }]}>
          {mediaStep === "none" && (
            <>
              <AgText variant="bodyLarge" weight="bold" center style={styles.title}>
                {task.task_text_ta}
              </AgText>
              <View style={styles.buttonList}>
                {BUTTONS.map((btn) => {
                  const Icon = btn.icon;
                  return (
                    <Pressable
                      key={btn.type}
                      disabled={submittingType !== null}
                      onPress={() => submit(btn.type)}
                      style={[styles.responseButton, { backgroundColor: btn.tone }]}
                      accessibilityRole="button"
                    >
                      {submittingType === btn.type ? (
                        <ActivityIndicator color="#FFFFFF" />
                      ) : (
                        <Icon size={22} color="#FFFFFF" />
                      )}
                      <AgText variant="bodyLarge" weight="semibold" style={styles.buttonLabel}>
                        {btn.label}
                      </AgText>
                    </Pressable>
                  );
                })}
              </View>
              <Pressable onPress={handleClose} style={styles.cancelRow} accessibilityRole="button">
                <AgText variant="body" style={{ color: colors.textMuted }}>
                  {t("dailyTask.cancel")}
                </AgText>
              </Pressable>
            </>
          )}

          {mediaStep === "photo" && (
            <PhotoUploadFlow
              taskId={task.id}
              onDone={() => setMediaStep(task.can_record_voice_note ? "voice" : "none")}
              onSkip={() => (task.can_record_voice_note ? setMediaStep("voice") : handleClose())}
            />
          )}

          {mediaStep === "voice" && (
            <VoiceNoteRecorder taskId={task.id} onDone={handleClose} onSkip={handleClose} />
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.4)" },
  sheet: { borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24 },
  title: { marginBottom: 16 },
  buttonList: { gap: 12 },
  responseButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    borderRadius: 16,
    paddingVertical: 16,
  },
  buttonLabel: { color: "#FFFFFF" },
  cancelRow: { alignItems: "center", paddingVertical: 12, marginTop: 4 },
});
