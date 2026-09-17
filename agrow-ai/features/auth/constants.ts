import { ScanLine, Sparkles, SunMedium, type LucideIcon } from 'lucide-react-native';

/** Onboarding carousel content. Text is resolved via i18n keys at render time. */
export interface OnboardingSlide {
  key: string;
  icon: LucideIcon;
  titleKey: string;
  bodyKey: string;
}

export const ONBOARDING_SLIDES: OnboardingSlide[] = [
  {
    key: 'advice',
    icon: Sparkles,
    titleKey: 'onboarding.slide1Title',
    bodyKey: 'onboarding.slide1Body',
  },
  {
    key: 'disease',
    icon: ScanLine,
    titleKey: 'onboarding.slide2Title',
    bodyKey: 'onboarding.slide2Body',
  },
  {
    key: 'weather-market',
    icon: SunMedium,
    titleKey: 'onboarding.slide3Title',
    bodyKey: 'onboarding.slide3Body',
  },
];
