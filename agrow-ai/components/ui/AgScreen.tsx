import { type ReactNode, useEffect, useState } from 'react';
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  View,
  type ScrollViewProps,
} from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/useAppTheme';
import { cn } from '@/utils/cn';

interface AgScreenProps {
  children: ReactNode;
  scroll?: boolean;
  padded?: boolean;
  keyboardAvoiding?: boolean;
  edges?: Edge[];
  className?: string;
  contentClassName?: string;
  contentContainerStyle?: ScrollViewProps['contentContainerStyle'];
  testID?: string;
  backgroundColor?: string;
  refreshControl?: ScrollViewProps['refreshControl'];
}

/**
 * Page scaffold: safe-area aware, themed background, optional scroll and
 * keyboard avoidance. Every screen renders inside an AgScreen.
 */
export function AgScreen({
  children,
  scroll = false,
  padded = true,
  keyboardAvoiding = false,
  edges = ['top', 'bottom'],
  className,
  contentClassName,
  contentContainerStyle,
  testID,
  backgroundColor,
  refreshControl,
}: AgScreenProps) {
  const { colors } = useAppTheme();
  // Android (edge-to-edge) does not resize the window for the keyboard, so a
  // scrolling screen gets extra bottom space equal to the keyboard height;
  // the user can then scroll every field and button above the keyboard.
  const androidScrollInset = keyboardAvoiding && scroll && Platform.OS === 'android';
  const keyboardHeight = useKeyboardHeight(androidScrollInset);
  const content = scroll ? (
    <ScrollView
      refreshControl={refreshControl}
      className="flex-1"
      style={{ flex: 1 }}
      contentContainerStyle={[
        { paddingHorizontal: padded ? 20 : 0, paddingBottom: 32 },
        contentContainerStyle,
        keyboardHeight > 0 ? { paddingBottom: keyboardHeight + 32 } : null,
      ]}
      contentContainerClassName={cn(padded && 'px-5', 'pb-8', contentClassName)}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      {children}
    </ScrollView>
  ) : (
    <View
      className={cn('flex-1', padded && 'px-5', contentClassName)}
      style={contentClassName ? undefined : { flex: 1, paddingHorizontal: padded ? 20 : 0 }}
    >
      {children}
    </View>
  );

  const body = keyboardAvoiding && !androidScrollInset ? (
    <KeyboardAvoidingView
      className="flex-1"
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {content}
    </KeyboardAvoidingView>
  ) : (
    content
  );

  return (
    <SafeAreaView
      testID={testID}
      className={cn('flex-1 bg-bg', className)}
      style={{ flex: 1, backgroundColor: backgroundColor ?? colors.bg }}
      edges={edges}
    >
      {body}
    </SafeAreaView>
  );
}

function useKeyboardHeight(enabled: boolean): number {
  const [height, setHeight] = useState(0);
  useEffect(() => {
    if (!enabled) return undefined;
    const show = Keyboard.addListener('keyboardDidShow', (e) => setHeight(e.endCoordinates.height));
    const hide = Keyboard.addListener('keyboardDidHide', () => setHeight(0));
    return () => { show.remove(); hide.remove(); };
  }, [enabled]);
  return height;
}
