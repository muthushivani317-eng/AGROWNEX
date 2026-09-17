import { useRef } from 'react';
import { FlatList, StyleSheet, View } from 'react-native';

import type { ChatMessage } from '../types';
import { ChatBubble } from './ChatBubble';
import { TypingIndicator } from './TypingIndicator';

/** Scrollable message thread that sticks to the latest message. */
export function MessageList({
  messages,
  isTyping,
  onRetryMessage,
}: {
  messages: ChatMessage[];
  isTyping: boolean;
  onRetryMessage: (message: ChatMessage) => void;
}) {
  const ref = useRef<FlatList<ChatMessage>>(null);

  return (
    <FlatList
      ref={ref}
      data={messages}
      keyExtractor={(m) => m.id}
      renderItem={({ item }) => (
        <View className="px-4 py-1" style={styles.messageRow}>
          <ChatBubble message={item} onRetry={() => onRetryMessage(item)} />
        </View>
      )}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      ListFooterComponent={
        isTyping ? (
          <View style={styles.messageRow}>
            <TypingIndicator />
          </View>
        ) : null
      }
      onContentSizeChange={() => ref.current?.scrollToEnd({ animated: true })}
      keyboardShouldPersistTaps="handled"
    />
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 16, paddingBottom: 10 },
  messageRow: { paddingHorizontal: 16, paddingVertical: 4 },
});
