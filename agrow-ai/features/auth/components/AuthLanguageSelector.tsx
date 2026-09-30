import { Globe2 } from 'lucide-react-native';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

interface AuthLanguageSelectorProps {
  variant?: 'default' | 'hero';
  compact?: boolean;
  style?: ViewStyle;
}

export function AuthLanguageSelector({
  variant = 'default',
  compact = false,
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
        compact && styles.compactRow,
        compact && variant === 'hero' && styles.compactHeroRow,
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
          compact && styles.compactOption,
          variant === 'hero' && language === 'ta' && styles.heroOptionSelected,
        ]}
        accessibilityRole="tab"
        accessibilityLabel={t('language.tamil')}
        accessibilityState={{ selected: language === 'ta' }}
      >
        <AgText
          variant={compact ? 'bodySmall' : 'body'}
          weight="semibold"
          style={{
            color:
              variant === 'hero'
                ? language === 'ta' ? '#FFFFFF' : '#46564C'
                : language === 'ta' ? colors.primary : colors.textMuted,
          }}
        >
          தமிழ்
        </AgText>
      </AgPressable>
      <View
        style={[
          styles.divider,
          { backgroundColor: variant === 'hero' ? '#D5DDD2' : colors.border },
        ]}
      />
      <AgPressable
        haptic={false}
        onPress={() => setLanguage('en')}
        style={[
          styles.option,
          variant === 'hero' && styles.heroOption,
          compact && styles.compactOption,
          variant === 'hero' && language === 'en' && styles.heroOptionSelected,
        ]}
        accessibilityRole="tab"
        accessibilityLabel={t('language.english')}
        accessibilityState={{ selected: language === 'en' }}
      >
        <AgText
          variant={compact ? 'bodySmall' : 'body'}
          weight="semibold"
          style={{
            color:
              variant === 'hero'
                ? language === 'en' ? '#FFFFFF' : '#46564C'
                : language === 'en' ? colors.primary : colors.textMuted,
          }}
        >
          {compact ? 'EN' : 'English'}
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
    borderRadius: 18,
    backgroundColor: 'rgba(255,253,246,0.94)',
    borderWidth: 1,
    borderColor: '#C8D2C6',
  },
  heroOption: {
    minHeight: 42,
    paddingHorizontal: 10,
    borderRadius: 15,
  },
  compactRow: { minHeight: 44, gap: 0 },
  compactHeroRow: { minHeight: 44, padding: 2, borderRadius: 16 },
  compactOption: { minHeight: 40, paddingHorizontal: 5, borderRadius: 14 },
  heroOptionSelected: {
    backgroundColor: '#176B3A',
  },
});
