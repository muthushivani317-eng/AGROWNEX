import { Component, type ReactNode, type ErrorInfo } from 'react';
import { Text, TouchableOpacity, View } from 'react-native';

import { logger } from '@/lib/logger';

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Last-resort crash guard. Renders a bilingual (Tamil-first) fallback instead of
 * a silent close when a descendant throws during render/lifecycle.
 *
 * Deliberately uses inline styles and no i18n/theme/NativeWind — those subsystems
 * are exactly what may have failed, so the boundary must not depend on them.
 *
 * NOTE: this catches JavaScript errors only. Native crashes (e.g. a native module
 * built for the wrong architecture) bypass React entirely and cannot be caught
 * here — for those, `adb logcat` is the source of truth. JS errors caught here
 * ARE reported to Crashlytics (via logger.error -> lib/logger.ts), so they show
 * up in the Firebase console once Crashlytics is enabled there.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    logger.error('ErrorBoundary', error, info.componentStack);
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    return (
      <View
        style={{
          flex: 1,
          justifyContent: 'center',
          alignItems: 'center',
          padding: 24,
          backgroundColor: '#fff',
        }}
      >
        <Text
          style={{
            fontSize: 20,
            fontWeight: 'bold',
            marginBottom: 12,
            textAlign: 'center',
            color: '#1a1a1a',
          }}
        >
          ஏதோ தவறு நடந்தது
        </Text>
        <Text
          style={{ fontSize: 16, color: '#666', marginBottom: 8, textAlign: 'center' }}
        >
          Something went wrong
        </Text>
        <Text
          style={{ fontSize: 12, color: '#999', marginBottom: 24, textAlign: 'center' }}
        >
          {this.state.error?.message}
        </Text>
        <TouchableOpacity
          onPress={() => this.setState({ hasError: false, error: null })}
          accessibilityRole="button"
          style={{
            backgroundColor: '#2D6A4F',
            paddingHorizontal: 24,
            paddingVertical: 12,
            borderRadius: 8,
          }}
        >
          <Text style={{ color: '#fff', fontSize: 16 }}>
            மீண்டும் முயற்சிக்கவும் / Retry
          </Text>
        </TouchableOpacity>
      </View>
    );
  }
}
