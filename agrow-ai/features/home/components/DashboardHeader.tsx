import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { CalendarDays } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { AgAvatar, AgPressable, AgText } from '@/components/ui';
import type { AuthUser } from '@/features/auth';
import { NotificationBell } from '@/features/notifications';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { greetingKey } from '@/utils/format';

import { useClock } from '../hooks/useClock';
import { formatClock } from '../utils/time';

/** Branded Home header with live local time and authenticated farmer identity. */
export function DashboardHeader({ user }: { user: AuthUser | null }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language, setLanguage } = useLanguage();
  const now = useClock();
  const displayName = user?.name?.trim() || t('home.farmerFallback');
  const date = now.toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <View>
      <View style={styles.topRow}>
        <View style={styles.brand} accessibilityLabel="AgrowNex">
          <Image
            source={require('@/assets/images/android-icon-foreground.png')}
            contentFit="contain"
            transition={0}
            style={styles.logo}
          />
          {/* One text node that shrinks to fit, so the name is never clipped
              by the language / bell / avatar buttons on narrow phones. */}
          <AgText
            variant="headingM"
            weight="bold"
            numberOfLines={1}
            adjustsFontSizeToFit
            minimumFontScale={0.7}
            maxFontSizeMultiplier={1.2}
            style={styles.wordmark}
          >
            Agrow<Text style={styles.wordmarkAI}>Nex</Text>
          </AgText>
        </View>
        <View style={styles.actions}>
          <AgPressable
            onPress={() => void setLanguage(language === 'ta' ? 'en' : 'ta')}
            accessibilityRole="button"
            accessibilityLabel={t('profile.changeLanguage')}
            style={styles.languageButton}
          >
            <AgText variant="bodySmall" weight="semibold" style={styles.languageText}>
              {language === 'ta' ? 'English' : 'தமிழ்'}
            </AgText>
          </AgPressable>
          <NotificationBell light />
          <AgPressable
            onPress={() => router.push('/profile')}
            accessibilityRole="button"
            accessibilityLabel={t('tabs.profile')}
            hitSlop={4}
            style={styles.profileButton}
          >
            <AgAvatar uri={user?.photoUrl} name={displayName} size={38} light />
          </AgPressable>
        </View>
      </View>

      <View style={styles.greeting}>
        <AgText variant="headingM" weight="bold" numberOfLines={3} style={styles.name}>
          {t(`home.${greetingKey(now)}`)}, {displayName}
        </AgText>
        <View style={styles.timeRow}>
          <CalendarDays size={17} color="#58685F" />
          <AgText variant="bodySmall" style={styles.timeText}>{date}</AgText>
          <View style={styles.timeDivider} />
          <AgText variant="bodySmall" style={styles.timeText}>{formatClock(now)}</AgText>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  topRow: { minHeight: 58, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  brand: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  logo: { width: 44, height: 44, flexShrink: 0 },
  wordmark: { flexShrink: 1, marginLeft: -4, color: '#173B2B' },
  wordmarkAI: { color: '#165B33' },
  actions: { flexShrink: 0, flexDirection: 'row', alignItems: 'center', gap: 6, paddingRight: 1 },
  languageButton: { minHeight: 40, paddingHorizontal: 10, borderRadius: 20, borderWidth: 1, borderColor: '#B9CCBC', backgroundColor: '#FFFDF8', alignItems: 'center', justifyContent: 'center' },
  languageText: { color: '#173B2B' },
  profileButton: { width: 44, height: 44, borderRadius: 22, borderWidth: 1.5, borderColor: '#165B33', backgroundColor: '#FFFDF8', alignItems: 'center', justifyContent: 'center' },
  greeting: { marginTop: 16 },
  name: { color: '#173B2B', lineHeight: 30 },
  timeRow: { marginTop: 7, flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 7 },
  timeText: { color: '#58685F' },
  timeDivider: { width: 1, height: 20, marginHorizontal: 5, backgroundColor: '#D8D5C9' },
});
