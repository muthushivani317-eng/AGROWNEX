import { useRouter } from 'expo-router';
import { ArrowLeft, Circle, History, Leaf, MessageCircle, SquarePen } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AgErrorState, AgSkeleton, AgOfflineBanner, AgText } from '@/components/ui';
import { useSelectedFarm } from '@/features/weather';

import { ChatComposer } from '../components/ChatComposer';
import { MessageList } from '../components/MessageList';
import { SuggestionChips } from '../components/SuggestionChips';
import { useChat } from '../hooks/useChat';

const CHAT_BG = '#F8F5EC';
const CHAT_SURFACE = '#FFFDF8';
const CHAT_GREEN = '#165B33';
const CHAT_BORDER = '#D9CDB5';
const CHAT_TEXT = '#173B2B';
const CHAT_MUTED = '#58685F';

function HeaderButton({
  icon,
  label,
  onPress,
  testID,
  disabled = false,
}: {
  icon: React.ReactNode;
  label: string;
  onPress: () => void;
  testID: string;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      disabled={disabled}
      accessibilityState={{ disabled }}
      onPress={onPress}
      activeOpacity={0.76}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={4}
      style={styles.headerButton}
    >
      {icon}
      <AgText
        variant="caption"
        weight="medium"
        numberOfLines={1}
        maxFontSizeMultiplier={1.25}
        style={styles.headerButtonLabel}
      >
        {label}
      </AgText>
    </TouchableOpacity>
  );
}

export function ChatScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { messages, isSending, send, retry, newChat, loadingHistory, historyError, retryHistory } = useChat();
  const { selected } = useSelectedFarm();
  const empty = messages.length === 0;
  const farmContext = selected
    ? [selected.name, selected.crop].filter(Boolean).join(' · ')
    : t('ai.noFarmContext');

  return (
    <SafeAreaView
      testID="ai-assistant-screen"
      style={styles.screen}
      edges={['top']}
    >
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          activeOpacity={0.76}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          style={styles.backButton}
        >
          <ArrowLeft size={26} color={CHAT_TEXT} />
        </TouchableOpacity>
        <View style={styles.brand} accessibilityLabel={t('ai.title')}>
          <View style={styles.brandIcon}>
            <Leaf size={25} color={CHAT_GREEN} />
          </View>
          <View style={styles.brandCopy}>
            <AgText variant="headingS" weight="bold" numberOfLines={2} style={styles.brandTitle}>{t('ai.farmAssistant')}</AgText>
            <AgText variant="caption" numberOfLines={1} style={styles.brandSubtitle}>AgrowAI</AgText>
          </View>
        </View>

        <View style={styles.headerActions}>
          <HeaderButton
            testID="ai-new-chat"
            disabled={isSending}
            icon={<SquarePen size={22} color={CHAT_TEXT} />}
            label={t('ai.newChat')}
            onPress={newChat}
          />
          <HeaderButton
            testID="ai-history"
            disabled={isSending}
            icon={<History size={22} color={CHAT_TEXT} />}
            label={t('ai.history')}
            onPress={() => router.push('/ai/history')}
          />
        </View>
      </View>

      <View style={styles.contextBar} accessibilityLabel={farmContext}>
        <View style={styles.contextFarm}>
          <View style={styles.contextIcon}><Leaf size={17} color={CHAT_GREEN} /></View>
          <AgText variant="bodySmall" weight="semibold" numberOfLines={2} style={styles.contextText}>{farmContext}</AgText>
        </View>
        <View style={styles.readyState}>
          <Circle size={10} fill="#3E9B3B" color="#3E9B3B" />
          <AgText variant="caption" weight="medium" numberOfLines={2} style={styles.readyText}>{t('ai.readyToHelp')}</AgText>
        </View>
      </View>

      <AgOfflineBanner />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {loadingHistory ? (
          <View style={styles.thread}>
            <AgSkeleton style={{ height: 100, margin: 16, borderRadius: 16 }} />
            <AgSkeleton style={{ height: 100, margin: 16, borderRadius: 16 }} />
          </View>
        ) : historyError ? (
          <View style={styles.thread}><AgErrorState light onRetry={retryHistory} /></View>
        ) : empty ? (
          <ScrollView
            style={styles.flex}
            contentContainerStyle={styles.emptyContent}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            <View style={styles.heroHaloOuter}>
              <View style={styles.heroHalo}>
                <MessageCircle size={54} strokeWidth={1.8} color={CHAT_GREEN} />
                <Leaf size={24} color={CHAT_GREEN} style={styles.heroLeaf} />
              </View>
            </View>

            <View style={styles.heroTitle} accessibilityLabel={t('ai.welcomeTitle')}>
              <AgText variant="headingL" weight="bold" style={styles.heroTitleText}>{t('ai.askPrefix')} </AgText>
              <AgText variant="headingL" weight="bold" style={styles.heroAccent}>AgrowAI</AgText>
            </View>
            <AgText variant="body" center style={styles.heroSubtitle}>
              {t('ai.welcomeMessage')}
            </AgText>

            <SuggestionChips onSelect={send} />
          </ScrollView>
        ) : (
          <View style={styles.thread}>
            <MessageList messages={messages} isTyping={isSending} onRetryMessage={retry} />
            {!isSending ? <SuggestionChips onSelect={send} compact /> : null}
          </View>
        )}

        <ChatComposer onSend={send} disabled={isSending || loadingHistory || historyError} />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  screen: { flex: 1, backgroundColor: CHAT_BG },
  header: {
    minHeight: 72,
    paddingHorizontal: 14,
    paddingVertical: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 6,
    backgroundColor: CHAT_BG,
  },
  backButton: { width: 48, height: 48, borderRadius: 12, borderWidth: 1, borderColor: CHAT_BORDER, backgroundColor: CHAT_SURFACE, alignItems: 'center', justifyContent: 'center' },
  brand: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 7 },
  brandIcon: { width: 42, height: 42, borderRadius: 21, borderWidth: 1, borderColor: '#B9CCBC', backgroundColor: CHAT_SURFACE, alignItems: 'center', justifyContent: 'center' },
  brandCopy: { flex: 1, minWidth: 0 },
  brandTitle: { color: CHAT_GREEN, fontSize: 17, lineHeight: 22 },
  brandSubtitle: { color: CHAT_MUTED },
  headerActions: { flexShrink: 0, flexDirection: 'row', alignItems: 'center', gap: 4 },
  headerButton: { minWidth: 50, minHeight: 56, paddingHorizontal: 3, alignItems: 'center', justifyContent: 'center', gap: 2 },
  headerButtonLabel: { color: CHAT_TEXT, fontSize: 10, lineHeight: 14 },
  contextBar: { marginHorizontal: 14, minHeight: 54, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 14, borderWidth: 1, borderColor: CHAT_BORDER, backgroundColor: CHAT_SURFACE, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  contextFarm: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 8 },
  contextIcon: { width: 30, height: 30, borderRadius: 15, backgroundColor: '#EDF3E8', alignItems: 'center', justifyContent: 'center' },
  contextText: { flex: 1, minWidth: 0, color: CHAT_TEXT },
  readyState: { maxWidth: '42%', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 5 },
  readyText: { flexShrink: 1, color: CHAT_GREEN, textAlign: 'right' },
  thread: { flex: 1, paddingTop: 4 },
  emptyContent: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 28,
    justifyContent: 'center',
  },
  heroHaloOuter: {
    width: 142,
    height: 142,
    borderRadius: 71,
    borderWidth: 1, borderColor: '#D7E2D2',
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroHalo: {
    width: 112,
    height: 112,
    borderRadius: 56,
    borderWidth: 1, borderColor: '#B9CCBC', backgroundColor: '#F0F4E9',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: CHAT_GREEN,
    shadowOpacity: 0.22,
    shadowRadius: 24,
    elevation: 5,
  },
  heroLeaf: { position: 'absolute', top: 24, right: 22 },
  heroTitle: { marginTop: 24, flexDirection: 'row', justifyContent: 'center', flexWrap: 'wrap' },
  heroTitleText: { color: CHAT_TEXT },
  heroAccent: { color: CHAT_GREEN },
  heroSubtitle: { marginTop: 10, marginHorizontal: 'auto', maxWidth: 560, lineHeight: 25, color: CHAT_MUTED },
});
