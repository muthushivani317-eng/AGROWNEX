import { Send, ShieldCheck, Sparkles } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, TextInput, TouchableOpacity, View } from 'react-native';

import { AgText } from '@/components/ui';

import { MAX_MESSAGE_CHARS } from '../constants';

/** Keyboard-safe multiline input using the existing send callback. */
export function ChatComposer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const [text, setText] = useState('');

  const canSend = text.trim().length > 0 && !disabled;
  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText('');
  };

  return (
    <View style={styles.container}>
      <View style={styles.inputShell}>
        <View style={styles.sparkleIcon} pointerEvents="none">
          <Sparkles size={20} color="#68756E" />
        </View>
        <TextInput
          testID="ai-composer-input"
          value={text}
          onChangeText={setText}
          placeholder={t('ai.placeholder')}
          placeholderTextColor="#7B857F"
          multiline
          maxLength={MAX_MESSAGE_CHARS}
          accessibilityLabel={t('ai.placeholder')}
          style={styles.input}
        />
        <TouchableOpacity
          testID="ai-send"
          onPress={submit}
          disabled={!canSend}
          activeOpacity={0.72}
          accessibilityRole="button"
          accessibilityLabel={t('ai.send')}
          accessibilityState={{ disabled: !canSend, busy: disabled }}
          style={[styles.send, canSend ? styles.sendEnabled : styles.sendDisabled]}
        >
          <Send size={21} color={canSend ? '#FFFFFF' : '#165B33'} />
        </TouchableOpacity>
      </View>
      <View style={styles.safetyRow}>
        <ShieldCheck size={17} color="#68756E" />
        <AgText variant="caption" style={styles.safetyText}>{t('ai.safetyNote')}</AgText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 16, paddingTop: 9, paddingBottom: 8, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: '#D9CDB5', backgroundColor: '#F8F5EC' },
  inputShell: {
    width: '100%', minHeight: 64, maxHeight: 136,
    borderRadius: 22, borderWidth: 1.5, borderColor: '#165B33', backgroundColor: '#FFFDF8',
    flexDirection: 'row', alignItems: 'center', overflow: 'hidden',
  },
  sparkleIcon: { width: 46, flexShrink: 0, alignItems: 'flex-end' },
  input: { flex: 1, minWidth: 0, minHeight: 60, maxHeight: 132, color: '#173B2B', fontSize: 16, lineHeight: 23, paddingHorizontal: 10, paddingVertical: 10 },
  send: { width: 48, height: 48, marginRight: 8, flexShrink: 0, borderRadius: 24, alignItems: 'center', justifyContent: 'center', zIndex: 2, elevation: 0, shadowOpacity: 0 },
  sendEnabled: { backgroundColor: '#165B33', borderWidth: 1, borderColor: '#0F4828' },
  sendDisabled: { backgroundColor: '#E6EFE2', borderWidth: 1, borderColor: '#9DBA91' },
  safetyRow: { marginTop: 9, paddingHorizontal: 4, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7 },
  safetyText: { flexShrink: 1, color: '#43564D', textAlign: 'center', lineHeight: 18 },
});
