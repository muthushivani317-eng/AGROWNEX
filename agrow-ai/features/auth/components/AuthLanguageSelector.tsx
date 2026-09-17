import { Globe2 } from 'lucide-react-native';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

interface AuthLanguageSelectorProps {
  variant?: 'default' | 'hero';
  style?: ViewStyle;
}

export function AuthLanguageSelector({
  variant = 'default',
  style,
}: AuthLanguageSelectorProps) {
  const { colors } = useAppTheme();
  const { language, setLanguage } = useLanguage();
  const { t } = useTranslation();

  return (
    <View
      style={[
        styles.row,
        variant === 'hero' && styles.heroRow,
        style,
      ]}
      accessibilityRole="tablist"
    >
      {variant === 'default' ? <Globe2 size={21} color={colors.primary} /> : null}
      <AgPressable
        haptic={false}
        onPress={() => setLanguage('ta')}
        style={[
          styles.option,
          variant === 'hero' && styles.heroOption,
          variant === 'hero' && language === 'ta' && styles.heroOptionSelected,
        ]}
        accessibilityRole="tab"
        accessibilityLabel={t('language.tamil')}
        accessibilityState={{ selected: language === 'ta' }}
      >
        <AgText
          weight="semibold"
          style={{
            color:
              variant === 'hero'
                ? language === 'ta' ? '#165B33' : '#46564C'
                : language === 'ta' ? colors.primary : colors.textMuted,
          }}
        >
          தமிழ்
        </AgText>
      </AgPressable>
      {variant === 'default' ? (
        <View style={[styles.divider, { backgroundColor: colors.border }]} />
      ) : null}
      <AgPressable
        haptic={false}
        onPress={() => setLanguage('en')}
        style={[
          styles.option,
          variant === 'hero' && styles.heroOption,
          variant === 'hero' && language === 'en' && styles.heroOptionSelected,
        ]}
        accessibilityRole="tab"
        accessibilityLabel={t('language.english')}
        accessibilityState={{ selected: language === 'en' }}
      >
        <AgText
          weight="semibold"
          style={{
            color:
              variant === 'hero'
                ? language === 'en' ? '#165B33' : '#46564C'
                : language === 'en' ? colors.primary : colors.textMuted,
          }}
        >
          English
        </AgText>
      </AgPressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, minHeight: 52 },
  option: { minHeight: 48, justifyContent: 'center', paddingHorizontal: 8 },
  divider: { width: 1, height: 20, marginHorizontal: 3 },
  heroRow: {
    minHeight: 48,
    gap: 0,
    padding: 3,
    borderRadius: 16,
    backgroundColor: 'rgba(255,253,246,0.94)',
    borderWidth: 1,
    borderColor: '#C8D2C6',
  },
  heroOption: {
    minHeight: 42,
    paddingHorizontal: 9,
    borderRadius: 13,
  },
  heroOptionSelected: {
    backgroundColor: '#E4F0DF',
    borderWidth: 1,
    borderColor: '#79A47F',
  },
});
