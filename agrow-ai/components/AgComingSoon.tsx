import { Hammer, type LucideIcon } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';

import { AgScreen } from './ui/AgScreen';
import { AgText } from './ui/AgText';

interface AgComingSoonProps {
  title: string;
  icon?: LucideIcon;
}

/**
 * Production placeholder for modules not yet built in this phase. Keeps the
 * shell navigable and on-brand rather than shipping a blank screen.
 */
export function AgComingSoon({ title, icon: Icon = Hammer }: AgComingSoonProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  return (
    <AgScreen>
      <View className="flex-1 items-center justify-center">
        <View className="mb-5 h-24 w-24 items-center justify-center rounded-full bg-primary/10">
          <Icon size={44} color={colors.primary} />
        </View>
        <AgText variant="headingM" weight="bold" center>
          {title}
        </AgText>
        <AgText variant="body" color="muted" center className="mt-2">
          {t('common.comingSoon')}
        </AgText>
      </View>
    </AgScreen>
  );
}
