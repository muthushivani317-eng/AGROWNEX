import { Image } from 'expo-image';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { AuthLanguageSelector } from './AuthLanguageSelector';

interface AuthHeroProps {
  height: number;
  compact?: boolean;
  showLanguageSelector?: boolean;
  showWelcome?: boolean;
  style?: ViewStyle;
}

export function AuthHero({
  height,
  compact = false,
  showLanguageSelector = false,
  showWelcome = false,
  style,
}: AuthHeroProps) {
  const { colors } = useAppTheme();
  const { t } = useTranslation();

  return (
    <View style={[styles.container, { height, backgroundColor: colors.primaryDark }, style]}>
      <Image
        source={require('@/assets/images/auth-hero.png')}
        contentFit="cover"
        contentPosition="center"
        style={StyleSheet.absoluteFill}
        accessibilityLabel={t('auth.heroImageAccessibility')}
      />
      <View style={[styles.scrim, { backgroundColor: compact ? 'rgba(8,47,25,0.52)' : 'rgba(8,47,25,0.22)' }]} />
      {compact ? (
        <View style={[styles.brandArea, styles.compactBrandArea]}>
          <Image
            source={require('@/assets/images/brand-wordmark.png')}
            contentFit="contain"
            style={[styles.wordmark, styles.compactWordmark]}
            accessibilityLabel={t('auth.brandAccessibility')}
          />
        </View>
      ) : (
        <>
          <View style={styles.heroTopBar}>
            <View
              style={styles.nativeBrand}
              accessible
              accessibilityLabel={t('auth.brandAccessibility')}
            >
              <Image
                source={require('@/assets/images/android-icon-foreground.png')}
                contentFit="contain"
                style={styles.emblem}
                accessible={false}
              />
              <View>
                <View style={styles.wordmarkRow}>
                  <AgText variant="headingS" weight="bold" style={styles.nativeWordmark}>
                    Agrow
                  </AgText>
                  <AgText variant="headingS" weight="bold" style={styles.nativeNex}>
                    Nex
                  </AgText>
                </View>
              </View>
            </View>
            {showLanguageSelector ? <AuthLanguageSelector variant="hero" /> : null}
          </View>
          {showWelcome ? (
            <View style={styles.welcomeCopy}>
              <AgText variant="headingXL" weight="bold" style={styles.welcomeTitle}>
                {t('auth.heroWelcome')}
              </AgText>
              <AgText variant="bodyLarge" weight="semibold" style={styles.welcomeSubtitle}>
                {t('auth.loginSubtitle')}
              </AgText>
            </View>
          ) : null}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { overflow: 'hidden' },
  scrim: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 },
  brandArea: { position: 'absolute', top: 20, left: 20, width: '58%' },
  compactBrandArea: { top: 18, left: 24 },
  wordmark: { width: 205, height: 78, borderRadius: 12 },
  compactWordmark: { width: 150, height: 58 },
  heroTopBar: {
    position: 'absolute',
    top: 12,
    right: 14,
    left: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  nativeBrand: {
    minWidth: 0,
    flexShrink: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  emblem: { width: 46, height: 46 },
  wordmarkRow: { marginLeft: -5, flexDirection: 'row', alignItems: 'baseline' },
  nativeWordmark: { color: '#165B33', letterSpacing: -0.8 },
  nativeNex: { color: '#F28A16', letterSpacing: -0.8 },
  welcomeCopy: {
    position: 'absolute',
    left: 20,
    right: '47%',
    bottom: 30,
  },
  welcomeTitle: {
    color: '#073F2A',
    fontSize: 31,
    letterSpacing: -1,
    lineHeight: 37,
    textShadowColor: 'rgba(255,253,248,0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 8,
  },
  welcomeSubtitle: {
    marginTop: 8,
    color: '#2F5144',
    fontSize: 16,
    lineHeight: 21,
    textShadowColor: 'rgba(255,253,248,0.85)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 7,
  },
});
