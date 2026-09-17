import { CheckCircle2, ImagePlus, Send, XCircle } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TextInput,
  View,
} from 'react-native';

import {
  AgBadge,
  AgCard,
  AgOfflineBanner,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { uploadService } from '@/features/profile/services/uploadProvider';
import { useAppTheme } from '@/hooks/useAppTheme';
import { pickPhoto } from '@/utils/image';

import { AttachmentViewer } from '../components/AttachmentViewer';
import { ConsultationStatusBadge } from '../components/ConsultationStatusBadge';
import { ExpertBackHeader } from '../components/ExpertBackHeader';
import { MessageBubble } from '../components/MessageBubble';
import { CATEGORY_LABEL_KEY, HISTORY_STATUSES } from '../constants';
import {
  useAddConsultationAttachment,
  useConsultationDetail,
  useReplyConsultation,
  useUpdateConsultationStatus,
} from '../hooks/useConsultations';
import { useExpertSync } from '../hooks/useExpertSync';
import type { ConsultationAttachment, ConsultationCategory } from '../types';

/** Consultation detail: the immutable conversation timeline + reply + resolve. */
export function ConsultationDetailScreen({ id }: { id: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  useExpertSync();

  const query = useConsultationDetail(id);
  const reply = useReplyConsultation(id);
  const addAttachment = useAddConsultationAttachment(id);
  const updateStatus = useUpdateConsultationStatus(id);

  const [draft, setDraft] = useState('');
  const [uploading, setUploading] = useState(false);
  const [viewer, setViewer] = useState<ConsultationAttachment | null>(null);

  const consultation = query.data;
  const isClosed =
    consultation != null &&
    (consultation.status === 'cancelled' || consultation.status === 'closed');
  const canResolve =
    consultation != null && !HISTORY_STATUSES.includes(consultation.status);

  const send = () => {
    if (!draft.trim()) return;
    reply.mutate(
      { body: draft.trim() },
      {
        onSuccess: (res) => {
          setDraft('');
          if (res.offline) Alert.alert(t('experts.savedOffline'));
        },
        onError: () => Alert.alert(t('experts.replyFailed')),
      },
    );
  };

  const attachPhoto = async () => {
    const uri = await pickPhoto();
    if (!uri) return;
    setUploading(true);
    try {
      const url = await uploadService.uploadImage(uri, 'experts');
      addAttachment.mutate({ fileUrl: url, kind: 'image' });
    } catch {
      Alert.alert(t('experts.uploadFailed'));
    } finally {
      setUploading(false);
    }
  };

  const resolve = () =>
    updateStatus.mutate({ status: 'resolved' }, {
      onError: () => Alert.alert(t('experts.statusFailed')),
    });

  const cancel = () =>
    Alert.alert(t('experts.cancelTitle'), t('experts.cancelPrompt'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('experts.cancelConfirm'),
        style: 'destructive',
        onPress: () => updateStatus.mutate({ status: 'cancelled' }),
      },
    ]);

  if (!consultation) {
    return (
      <AgScreen>
        <ExpertBackHeader title={t('experts.detailTitle')} />
        <View className="mt-4 gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} className="h-20 w-full rounded-card" />
          ))}
        </View>
      </AgScreen>
    );
  }

  return (
    <AgScreen padded={false}>
      <AgOfflineBanner />
      <View className="px-5 pt-1">
        <ExpertBackHeader
          title={consultation.subject}
          right={<ConsultationStatusBadge status={consultation.status} />}
        />
      </View>

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <ScrollView
          className="flex-1 px-5"
          contentContainerClassName="gap-3 py-3 pb-6"
          keyboardShouldPersistTaps="handled"
        >
          <AgCard className="gap-2">
            <View className="flex-row flex-wrap items-center gap-1.5">
              <AgBadge
                label={t(
                  CATEGORY_LABEL_KEY[consultation.category as ConsultationCategory] ??
                    'experts.categoryGeneral',
                )}
                tone="neutral"
              />
              {consultation.crop ? <AgBadge label={consultation.crop} tone="info" /> : null}
            </View>
            {consultation.expert ? (
              <AgText variant="bodySmall" color="muted">
                {t('experts.assignedTo', { name: consultation.expert.fullName })}
              </AgText>
            ) : (
              <AgText variant="bodySmall" color="muted">
                {t('experts.assigningDesk')}
              </AgText>
            )}
            {consultation.resolutionNote ? (
              <AgText variant="bodySmall">
                {t('experts.resolutionNote')}: {consultation.resolutionNote}
              </AgText>
            ) : null}
          </AgCard>

          {consultation.messages.map((m) => (
            <MessageBubble key={m.id} message={m} onOpenAttachment={setViewer} />
          ))}

          {canResolve ? (
            <View className="mt-2 flex-row gap-2">
              <AgPressable
                onPress={resolve}
                accessibilityRole="button"
                accessibilityLabel={t('experts.markResolved')}
                className="flex-1 flex-row items-center justify-center gap-1.5 rounded-md bg-success/12 py-3"
              >
                <CheckCircle2 size={18} color={colors.success} />
                <AgText variant="bodySmall" weight="semibold" style={{ color: colors.success }}>
                  {t('experts.markResolved')}
                </AgText>
              </AgPressable>
              <AgPressable
                onPress={cancel}
                accessibilityRole="button"
                accessibilityLabel={t('experts.cancelConsultation')}
                className="flex-1 flex-row items-center justify-center gap-1.5 rounded-md bg-danger/10 py-3"
              >
                <XCircle size={18} color={colors.danger} />
                <AgText variant="bodySmall" weight="semibold" style={{ color: colors.danger }}>
                  {t('experts.cancelConsultation')}
                </AgText>
              </AgPressable>
            </View>
          ) : null}
        </ScrollView>

        {/* Reply composer — hidden once the thread is cancelled/closed. */}
        {!isClosed ? (
          <View className="flex-row items-end gap-2 border-t border-border bg-surface px-4 py-2.5">
            <AgPressable
              onPress={attachPhoto}
              disabled={uploading}
              accessibilityRole="button"
              accessibilityLabel={t('experts.addPhoto')}
              className="h-11 w-11 items-center justify-center rounded-full bg-surface-card"
            >
              {uploading ? (
                <ActivityIndicator color={colors.primary} />
              ) : (
                <ImagePlus size={20} color={colors.primary} />
              )}
            </AgPressable>
            <View className="max-h-28 flex-1 justify-center rounded-2xl bg-surface-card px-4 py-1">
              <ComposerInput
                value={draft}
                onChange={setDraft}
                placeholder={t('experts.replyPlaceholder')}
              />
            </View>
            <AgPressable
              onPress={send}
              disabled={!draft.trim() || reply.isPending}
              accessibilityRole="button"
              accessibilityLabel={t('experts.send')}
              className={`h-11 w-11 items-center justify-center rounded-full ${
                draft.trim() ? 'bg-primary' : 'bg-primary/40'
              }`}
            >
              <Send size={18} color={colors.onPrimary} />
            </AgPressable>
          </View>
        ) : null}
      </KeyboardAvoidingView>

      <AttachmentViewer
        uri={viewer?.fileUrl ?? null}
        caption={viewer?.caption}
        onClose={() => setViewer(null)}
      />
    </AgScreen>
  );
}

// A minimal multiline text input kept inline so the composer stays self-contained.
function ComposerInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const { colors } = useAppTheme();
  return (
    <TextInput
      value={value}
      onChangeText={onChange}
      placeholder={placeholder}
      placeholderTextColor={colors.textMuted}
      multiline
      style={{ color: colors.text, paddingVertical: 6, fontSize: 15 }}
      accessibilityLabel={placeholder}
    />
  );
}
