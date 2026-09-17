import { Leaf, RefreshCw, TriangleAlert } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StyleSheet, TouchableOpacity, View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { ChatMessage } from '../types';

/** A single chat bubble — farmer (right, primary) or assistant (left, card). */
export function ChatBubble({ message, onRetry }: { message: ChatMessage; onRetry?: () => void }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const isUser = message.sender === 'user';
  // Strip lightweight markdown bold markers for clean on-device rendering.
  const text = message.error ? t(message.errorMessageKey ?? 'ai.errorReply') : message.text.replace(/\*\*/g, '');
  const time = message.createdAt
    ? new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <View style={[styles.turn, isUser ? styles.userTurn : styles.assistantTurn]}>
      {!isUser ? (
        <View style={styles.avatar} accessible={false} importantForAccessibility="no-hide-descendants">
          <Leaf size={20} color="#165B33" />
        </View>
      ) : null}
      <View style={[styles.bubbleColumn, isUser && styles.userColumn]}>
        <TouchableOpacity
          onPress={message.sendFailed ? onRetry : undefined}
          disabled={!message.sendFailed || !onRetry}
          activeOpacity={message.sendFailed ? 0.72 : 1}
          style={[
            styles.bubble,
            isUser ? styles.userBubble : styles.assistantBubble,
            message.sendFailed && styles.failedBubble,
            message.error && styles.errorBubble,
          ]}
        >
          <AgText
            variant="body"
            color="inherit"
            style={
              message.error
                ? styles.errorText
                : isUser && !message.sendFailed
                  ? styles.userText
                  : styles.assistantText
            }
          >
            {text}
          </AgText>
          {message.sendFailed ? (
            <View className="mt-1 flex-row items-center gap-1">
              <RefreshCw size={12} color={colors.warning} />
              <AgText variant="caption" style={styles.retryText}>{t('ai.retrySend')}</AgText>
            </View>
          ) : null}
        </TouchableOpacity>
        {time ? <AgText variant="caption" color="inherit" style={[styles.time, isUser && styles.userTime]}>{time}</AgText> : null}
        {!isUser && !message.error ? (
          <View style={styles.verifyRow}>
            <TriangleAlert size={14} color="#A76B00" />
            <AgText variant="caption" style={styles.verifyText}>{t('ai.verifyInField')}</AgText>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  turn: { width: '100%', flexDirection: 'row', alignItems: 'flex-start', gap: 9 },
  userTurn: { justifyContent: 'flex-end' },
  assistantTurn: { justifyContent: 'flex-start' },
  avatar: { width: 40, height: 40, borderRadius: 20, borderWidth: 1, borderColor: '#165B33', backgroundColor: '#FFFDF8', alignItems: 'center', justifyContent: 'center' },
  bubbleColumn: { maxWidth: '82%', alignItems: 'flex-start' },
  userColumn: { alignItems: 'flex-end' },
  bubble: { paddingHorizontal: 15, paddingVertical: 11, borderRadius: 16 },
  userBubble: { backgroundColor: '#DDEDD7', borderWidth: 1.5, borderColor: '#165B33', borderBottomRightRadius: 4 },
  assistantBubble: { backgroundColor: '#FFFDF8', borderWidth: 1, borderColor: '#165B33', borderBottomLeftRadius: 4 },
  failedBubble: { backgroundColor: '#FFF8E8', borderWidth: 1, borderStyle: 'dashed', borderColor: '#C27A00' },
  errorBubble: { backgroundColor: '#FFF1EE', borderWidth: 1, borderColor: '#C84A3A' },
  userText: { color: '#173B2B' },
  assistantText: { color: '#173B2B' },
  errorText: { color: '#A93A2D' },
  time: { color: '#6A756F', marginTop: 3 },
  userTime: { textAlign: 'right' },
  retryText: { color: '#775000' },
  verifyRow: { marginTop: 6, minHeight: 30, paddingHorizontal: 9, paddingVertical: 5, borderRadius: 8, backgroundColor: '#FFF4D6', flexDirection: 'row', alignItems: 'center', gap: 6 },
  verifyText: { color: '#775000' },
});
