import fs from 'node:fs';
import path from 'node:path';

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, '../../..', relative), 'utf8');

describe('AI Assistant screen contract', () => {
  const screen = read('features/ai/screens/ChatScreen.tsx');
  const suggestions = read('features/ai/components/SuggestionChips.tsx');
  const composer = read('features/ai/components/ChatComposer.tsx');
  const bubble = read('features/ai/components/ChatBubble.tsx');
  const hook = read('features/ai/hooks/useChat.ts');

  it('keeps the existing new-chat and history behavior', () => {
    expect(screen).toContain('onPress={newChat}');
    expect(screen).toContain("router.push('/ai/history')");
  });

  it('sends localized suggestions through the real chat callback', () => {
    expect(screen).toContain('<SuggestionChips onSelect={send} />');
    expect(suggestions).toContain('onPress={() => onSelect(prompt)}');
  });

  it('keeps active conversations and keyboard-safe composition', () => {
    expect(screen).toContain('<MessageList messages={messages}');
    expect(screen).toContain('<KeyboardAvoidingView');
    expect(composer).toContain('onSend(value)');
    expect(composer).toContain('multiline');
    expect(composer).toContain("flexDirection: 'row', alignItems: 'center'");
    expect(composer).toContain("width: 48, height: 48, marginRight: 8");
    expect(composer).toContain("input: { flex: 1, minWidth: 0");
    expect(composer).toContain('<TouchableOpacity');
    expect(composer).toContain("zIndex: 2, elevation: 0, shadowOpacity: 0");
  });

  it('does not advertise unavailable voice input', () => {
    expect(composer).not.toContain('Microphone');
    expect(composer).not.toContain('Mic size');
  });

  it('renders the approved bilingual-ready farm conversation structure', () => {
    expect(screen).toContain("t('ai.farmAssistant')");
    expect(screen).toContain("t('ai.readyToHelp')");
    expect(screen).toContain('<MessageList messages={messages}');
    expect(screen).toContain('<SuggestionChips onSelect={send} compact />');
    expect(bubble).toContain("message.sender === 'user'");
    expect(bubble).toContain("backgroundColor: '#DDEDD7'");
    expect(bubble).toContain("userText: { color: '#173B2B' }");
    expect(bubble).toContain('<TouchableOpacity');
    expect(bubble).toContain('color="inherit"');
    expect(bubble).toContain("t('ai.verifyInField')");
  });

  it('uses fixed readable colors on every light chat surface', () => {
    expect(suggestions).toContain("backgroundColor: '#FFFDF8'");
    expect(suggestions).toContain("prompt: { flex: 1, minWidth: 0, color: '#173B2B' }");
    expect(suggestions).not.toContain('useAppTheme');
    expect(screen).not.toContain('color="muted"');
    expect(composer).toContain("color: '#173B2B'");
    expect(suggestions).not.toContain('<AgPressable');
  });

  it('marks an active local thread authoritative before appending the farmer question', () => {
    const authorityGuard = hook.indexOf('hydratedConversationIdRef.current = activeConversationId');
    const optimisticAppend = hook.indexOf('setMessages((prev) => [...prev, userMessage])');
    expect(authorityGuard).toBeGreaterThan(-1);
    expect(optimisticAppend).toBeGreaterThan(authorityGuard);
  });
});
