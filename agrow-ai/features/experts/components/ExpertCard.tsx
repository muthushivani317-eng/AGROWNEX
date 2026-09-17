import { BadgeCheck } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgCard, AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { CATEGORY_LABEL_KEY, EXPERT_TYPE_LABEL_KEY } from '../constants';
import type { ConsultationCategory, Expert, ExpertType } from '../types';
import { expertTypeIcon } from './expertIcon';

interface Props {
  expert: Expert;
  onPress?: (expert: Expert) => void;
}

/** A verified expert desk summary row. */
export function ExpertCard({ expert, onPress }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon = expertTypeIcon(expert.expertType);
  const typeLabel =
    EXPERT_TYPE_LABEL_KEY[expert.expertType as ExpertType] ?? 'experts.typePrivate';

  return (
    <AgPressable
      onPress={onPress ? () => onPress(expert) : undefined}
      accessibilityRole="button"
      accessibilityLabel={expert.fullName}
    >
      <AgCard className="flex-row gap-3">
        <View
          className="h-11 w-11 items-center justify-center rounded-full"
          style={{ backgroundColor: `${colors.primary}1A` }}
        >
          <Icon size={22} color={colors.primary} />
        </View>
        <View className="flex-1 gap-1">
          <View className="flex-row items-center gap-1">
            <AgText variant="body" weight="semibold" numberOfLines={1} className="flex-1">
              {expert.fullName}
            </AgText>
            {expert.verified ? <BadgeCheck size={16} color={colors.primary} /> : null}
          </View>
          {expert.organization ? (
            <AgText variant="caption" color="muted" numberOfLines={1}>
              {expert.organization}
            </AgText>
          ) : null}
          <View className="mt-1 flex-row flex-wrap items-center gap-1.5">
            <AgBadge label={t(typeLabel)} tone="info" />
            {expert.categories.slice(0, 2).map((c) => (
              <AgBadge
                key={c}
                label={t(CATEGORY_LABEL_KEY[c as ConsultationCategory] ?? 'experts.categoryGeneral')}
                tone="neutral"
              />
            ))}
          </View>
        </View>
      </AgCard>
    </AgPressable>
  );
}
