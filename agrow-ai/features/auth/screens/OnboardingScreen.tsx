import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FlatList,
  useWindowDimensions,
  View,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AgLanguageToggle } from '@/components/AgLanguageToggle';
import { AgButton, AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { cn } from '@/utils/cn';

import { ONBOARDING_SLIDES, type OnboardingSlide } from '../constants';
import { useAuthStore } from '../store/authStore';

function Slide({ slide, width }: { slide: OnboardingSlide; width: number }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon = slide.icon;
  return (
    <View style={{ width }} className="items-center justify-center px-8">
      <View className="mb-10 h-44 w-44 items-center justify-center rounded-full bg-primary/10">
        <View className="h-28 w-28 items-center justify-center rounded-full bg-primary/15">
          <Icon size={56} color={colors.primary} />
        </View>
      </View>
      <AgText variant="headingL" weight="bold" center>
        {t(slide.titleKey)}
      </AgText>
      <AgText variant="body" color="muted" center className="mt-3">
        {t(slide.bodyKey)}
      </AgText>
    </View>
  );
}

export function OnboardingScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const listRef = useRef<FlatList<OnboardingSlide>>(null);
  const [index, setIndex] = useState(0);
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);

  const isLast = index === ONBOARDING_SLIDES.length - 1;

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const next = Math.round(e.nativeEvent.contentOffset.x / width);
    if (next !== index) setIndex(next);
  };

  const finish = async () => {
    await completeOnboarding();
    router.replace('/(auth)/login');
  };

  const goNext = () => {
    if (isLast) return finish();
    listRef.current?.scrollToOffset({ offset: (index + 1) * width, animated: true });
  };

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top', 'bottom']}>
      <View className="flex-row items-center justify-between px-5 py-2">
        <AgLanguageToggle />
        <AgPressable haptic={false} onPress={finish} className="px-2 py-1">
          <AgText variant="body" weight="semibold" color="muted">
            {t('common.skip')}
          </AgText>
        </AgPressable>
      </View>

      <View className="flex-1">
        <FlatList
          ref={listRef}
          data={ONBOARDING_SLIDES}
          keyExtractor={(s) => s.key}
          renderItem={({ item }) => <Slide slide={item} width={width} />}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onMomentumScrollEnd={onScroll}
          bounces={false}
        />
      </View>

      <View className="px-6 pb-4">
        <View className="mb-6 flex-row justify-center gap-2">
          {ONBOARDING_SLIDES.map((s, i) => (
            <View
              key={s.key}
              className={cn(
                'h-2 rounded-full',
                i === index ? 'w-6 bg-primary' : 'w-2 bg-border',
              )}
            />
          ))}
        </View>
        <AgButton
          title={isLast ? t('common.getStarted') : t('common.next')}
          onPress={goNext}
          size="lg"
        />
      </View>
    </SafeAreaView>
  );
}
