import { useState } from 'react';
import { Modal, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgButton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import type { BananaFeedbackChoice } from '../types';

const CHOICES: BananaFeedbackChoice[] = [
  'CORRECT',
  'INCORRECT',
  'UNSURE',
  'IMAGE_POOR',
  'NOT_BANANA',
  'OTHER',
];

export function BananaFeedbackSheet({
  visible,
  submitting,
  onClose,
  onSubmit,
}: {
  visible: boolean;
  submitting: boolean;
  onClose: () => void;
  onSubmit: (choice: BananaFeedbackChoice, notes?: string) => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [choice, setChoice] = useState<BananaFeedbackChoice | null>(null);
  const [notes, setNotes] = useState('');
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View
        style={[styles.backdrop, { backgroundColor: `${colors.bg}66` }]}
      >
        <View
          style={[
            styles.sheet,
            { backgroundColor: colors.card, borderColor: colors.border },
          ]}
        >
          <AgText variant="headingS" weight="bold">
            {t('banana.ui.feedbackTitle')}
          </AgText>
          <View style={styles.choices}>
            {CHOICES.map((item) => (
              <Pressable
                key={item}
                accessibilityRole="button"
                accessibilityLabel={t(`banana.feedback.${item}`)}
                onPress={() => setChoice(item)}
                style={[
                  styles.choice,
                  {
                    backgroundColor:
                      choice === item ? colors.primary : colors.surface,
                  },
                ]}
              >
                <AgText color={choice === item ? 'onPrimary' : 'default'}>
                  {t(`banana.feedback.${item}`)}
                </AgText>
              </Pressable>
            ))}
          </View>
          <TextInput
            value={notes}
            onChangeText={setNotes}
            placeholder={t('banana.ui.feedbackNotes')}
            multiline
            maxLength={2000}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.notes,
              {
                color: colors.text,
                borderColor: colors.border,
                backgroundColor: colors.surface,
              },
            ]}
          />
          <AgButton
            title={t('banana.ui.sendFeedback')}
            disabled={!choice}
            loading={submitting}
            onPress={() =>
              choice && onSubmit(choice, notes.trim() || undefined)
            }
          />
          <AgButton
            title={t('common.cancel')}
            variant="ghost"
            onPress={onClose}
          />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  sheet: {
    padding: 20,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderWidth: 1,
  },
  choices: {
    marginVertical: 12,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  choice: {
    minHeight: 48,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    justifyContent: 'center',
  },
  notes: {
    minHeight: 80,
    marginBottom: 12,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    textAlignVertical: 'top',
  },
});
