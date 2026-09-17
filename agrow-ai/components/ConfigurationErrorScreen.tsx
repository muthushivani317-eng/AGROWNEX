import { Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ConfigurationErrorCategory } from '@/config/env';
import { useAppTheme } from '@/hooks/useAppTheme';

interface Props {
  category: ConfigurationErrorCategory;
}

/**
 * Dependency-free startup fallback for a misconfigured production bundle.
 * It intentionally does not display endpoint values or exception details.
 */
export function ConfigurationErrorScreen({ category }: Props) {
  const { colors } = useAppTheme();
  const { t } = useTranslation();
  return (
    <View
      testID="configuration-error-screen"
      accessibilityRole="alert"
      style={{
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 28,
        backgroundColor: colors.bg,
      }}
    >
      <Text
        style={{
          color: colors.primary,
          fontSize: 22,
          fontWeight: '700',
          textAlign: 'center',
          marginBottom: 14,
        }}
      >
        {t('configurationError.title')}
      </Text>
      <Text style={{ color: colors.text, fontSize: 16, textAlign: 'center', marginBottom: 10 }}>
        {t('configurationError.message')}
      </Text>
      <Text style={{ color: colors.textMuted, fontSize: 14, textAlign: 'center' }}>
        {t('configurationError.supportMessage')}
      </Text>
      <Text testID="configuration-error-category" style={{ marginTop: 20, color: colors.textMuted }}>
        {category}
      </Text>
    </View>
  );
}
