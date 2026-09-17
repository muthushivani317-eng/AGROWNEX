import { ImagePlus, X } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, Alert, Image, Pressable, View } from 'react-native';

import { AgButton, AgCard, AgDropdown, AgInput, AgPressable, AgText } from '@/components/ui';
import { useFarms } from '@/features/farm';
import { uploadService } from '@/features/profile/services/uploadProvider';
import { useAppTheme } from '@/hooks/useAppTheme';
import { pickPhoto } from '@/utils/image';

import {
  CATEGORIES,
  CATEGORY_LABEL_KEY,
  PRIORITIES,
  PRIORITY_LABEL_KEY,
} from '../constants';
import type {
  AttachmentInput,
  ConsultationCategory,
  ConsultationInput,
  ConsultationPriority,
} from '../types';

interface Props {
  submitting: boolean;
  onSubmit: (input: ConsultationInput) => void;
  presetExpertId?: string | null;
}

/** Create-consultation form (docs flow: crop → issue → photos → description). */
export function ConsultationForm({ submitting, onSubmit, presetExpertId }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { data: farmsData } = useFarms();
  const farms = farmsData?.items ?? [];

  const [farmId, setFarmId] = useState<string>('');
  const [category, setCategory] = useState<ConsultationCategory>('crop_disease');
  const [crop, setCrop] = useState('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<ConsultationPriority>('medium');
  const [attachments, setAttachments] = useState<AttachmentInput[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const farmOptions = useMemo(
    () => [
      { value: '', label: t('experts.noFarm') },
      ...farms.map((f) => ({ value: f.id, label: f.name })),
    ],
    [farms, t],
  );

  const addPhoto = async () => {
    const uri = await pickPhoto();
    if (!uri) return;
    setUploading(true);
    try {
      const url = await uploadService.uploadImage(uri, 'experts');
      setAttachments((prev) => [...prev, { fileUrl: url, kind: 'image' }]);
    } catch {
      Alert.alert(t('experts.uploadFailed'));
    } finally {
      setUploading(false);
    }
  };

  const submit = () => {
    if (subject.trim().length < 3) {
      setError(t('experts.errorSubject'));
      return;
    }
    if (description.trim().length < 5) {
      setError(t('experts.errorDescription'));
      return;
    }
    setError(null);
    onSubmit({
      farmId: farmId || null,
      category,
      crop: crop.trim() || (farmId ? farms.find((f) => f.id === farmId)?.crop ?? null : null),
      subject: subject.trim(),
      description: description.trim(),
      priority,
      preferredExpertId: presetExpertId ?? null,
      attachments,
    });
  };

  return (
    <View className="gap-4">
      <AgDropdown
        label={t('experts.farm')}
        placeholder={t('experts.noFarm')}
        value={farmId}
        options={farmOptions}
        onChange={setFarmId}
      />
      <AgDropdown
        label={t('experts.category')}
        placeholder={t('experts.category')}
        value={category}
        options={CATEGORIES.map((c) => ({ value: c, label: t(CATEGORY_LABEL_KEY[c]) }))}
        onChange={(v) => setCategory(v as ConsultationCategory)}
      />
      <AgInput
        label={t('experts.crop')}
        placeholder={t('experts.cropPlaceholder')}
        value={crop}
        onChangeText={setCrop}
      />
      <AgInput
        label={t('experts.subject')}
        placeholder={t('experts.subjectPlaceholder')}
        value={subject}
        onChangeText={setSubject}
        maxLength={160}
      />
      <AgInput
        label={t('experts.description')}
        placeholder={t('experts.descriptionPlaceholder')}
        value={description}
        onChangeText={setDescription}
        multiline
        numberOfLines={5}
        maxLength={4000}
      />
      <AgDropdown
        label={t('experts.priority')}
        placeholder={t('experts.priority')}
        value={priority}
        options={PRIORITIES.map((p) => ({ value: p, label: t(PRIORITY_LABEL_KEY[p]) }))}
        onChange={(v) => setPriority(v as ConsultationPriority)}
      />

      {/* Photos (optional) + a reserved voice-note note (future-ready). */}
      <View className="gap-2">
        <AgText variant="label" weight="semibold" color="muted">
          {t('experts.photos')}
        </AgText>
        <View className="flex-row flex-wrap gap-2">
          {attachments.map((a, index) => (
            <View key={a.fileUrl} className="h-20 w-20">
              <Image
                source={{ uri: a.fileUrl }}
                className="h-20 w-20 rounded-lg"
                resizeMode="cover"
              />
              <Pressable
                onPress={() =>
                  setAttachments((prev) => prev.filter((_, i) => i !== index))
                }
                accessibilityRole="button"
                accessibilityLabel={t('common.delete')}
                className="absolute -right-1.5 -top-1.5 h-6 w-6 items-center justify-center rounded-full bg-danger"
              >
                <X size={14} color="#fff" />
              </Pressable>
            </View>
          ))}
          <AgPressable
            onPress={addPhoto}
            disabled={uploading}
            accessibilityRole="button"
            accessibilityLabel={t('experts.addPhoto')}
            className="h-20 w-20 items-center justify-center rounded-lg border border-dashed border-border bg-surface-card"
          >
            {uploading ? (
              <ActivityIndicator color={colors.primary} />
            ) : (
              <ImagePlus size={22} color={colors.primary} />
            )}
          </AgPressable>
        </View>
        <AgText variant="caption" color="muted">
          {t('experts.voiceComingSoon')}
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
        title={t('experts.submit')}
        variant="primary"
        onPress={submit}
        loading={submitting}
        disabled={uploading}
      />
    </View>
  );
}
