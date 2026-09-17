import { useRouter } from 'expo-router';
import { ArrowLeft, MessageSquare, Trash2 } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, FlatList, Pressable, StyleSheet, View } from 'react-native';

import {
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import {
  useConversations,
  useDeleteConversation,
} from '../hooks/useConversations';
import { useChatStore } from '../store/chatStore';
import type { Conversation } from '../types';

export function HistoryScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const setActive = useChatStore((s) => s.setActive);

  const { data, isLoading, isError, isRefetching, refetch } = useConversations();
  const remove = useDeleteConversation();

  const open = (id: string) => {
    setActive(id);
    router.back();
  };

  const confirmDelete = (conversation: Conversation) => {
    Alert.alert(t('ai.deleteConfirmTitle'), t('ai.deleteConfirmMessage'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: () => {
          if (remove.isPending) return;
          remove.mutate(conversation.id, { onError: () => Alert.alert(t('common.somethingWrong')) });
        },
      },
    ]);
  };

  const header = (
    <View style={{ marginVertical: 8, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      <Pressable
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel={t('common.back')}
        style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}
      >
        <ArrowLeft size={24} color="#173B2B" />
      </Pressable>
      <AgText variant="headingM" weight="bold" style={styles.primaryText}>
        {t('ai.historyTitle')}
      </AgText>
    </View>
  );

  if (isLoading) {
    return (
      <AgScreen backgroundColor="#F8F5EC">
        {header}
        <View className="gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} style={{ height: 64, width: '100%', borderRadius: 16 }} />
          ))}
        </View>
      </AgScreen>
    );
  }

  if (isError) {
    return (
      <AgScreen backgroundColor="#F8F5EC">
        {header}
        <AgErrorState light onRetry={() => void refetch()} />
      </AgScreen>
    );
  }

  const conversations = data ?? [];

  return (
    <AgScreen padded={false} backgroundColor="#F8F5EC">
      <View style={{ flex: 1, paddingHorizontal: 20 }}>
        <FlatList
          data={conversations}
          refreshing={isRefetching}
          onRefresh={() => void refetch()}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={header}
          contentContainerStyle={{ paddingBottom: 32, gap: 8, flexGrow: 1 }}
          renderItem={({ item }) => (
            <AgPressable
              onPress={() => open(item.id)}
              accessibilityRole="button"
              accessibilityLabel={item.title ?? t('ai.title')}
            >
              <AgCard style={styles.card} className="flex-row items-center gap-3">
                <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                  <MessageSquare size={16} color={colors.primary} />
                </View>
                <View className="flex-1">
                  <AgText variant="body" weight="semibold" numberOfLines={1} style={styles.primaryText}>
                    {item.title ?? t('ai.title')}
                  </AgText>
                  {item.lastMessage ? (
                    <AgText variant="caption" numberOfLines={1} style={styles.mutedText}>
                      {item.lastMessage.replace(/\*\*/g, '')}
                    </AgText>
                  ) : null}
                </View>
                <AgPressable
                  onPress={() => confirmDelete(item)}
                  accessibilityRole="button"
                  accessibilityLabel={t('common.delete')}
                  className="h-9 w-9 items-center justify-center"
                >
                  <Trash2 size={17} color="#58685F" />
                </AgPressable>
              </AgCard>
            </AgPressable>
          )}
          ListEmptyComponent={
            <AgEmptyState
              light
              icon={MessageSquare}
              title={t('ai.noConversationsTitle')}
              message={t('ai.noConversationsMessage')}
            />
          }
        />
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFDF8', borderColor: '#D9CDB5' },
  primaryText: { color: '#173B2B' },
  mutedText: { color: '#58685F' },
});
