import { MessagesSquare, Paperclip } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgCard, AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { CATEGORY_LABEL_KEY, PRIORITY_LABEL_KEY, PRIORITY_TONE } from '../constants';
import type { Consultation, ConsultationCategory, ConsultationPriority } from '../types';
import { relativeTimeKey } from '../utils/time';
import { ConsultationStatusBadge } from './ConsultationStatusBadge';

interface Props {
  consultation: Consultation;
  onPress: (consultation: Consultation) => void;
}

/** A consultation summary row for the lists. */
export function ConsultationCard({ consultation, onPress }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const rt = relativeTimeKey(consultation.lastMessageAt ?? consultation.createdAt);
  const priority = consultation.priority as ConsultationPriority;

  return (
    <AgPressable
      onPress={() => onPress(consultation)}
      accessibilityRole="button"
      accessibilityLabel={consultation.subject}
    >
      <AgCard className="gap-2">
        <View className="flex-row items-start justify-between gap-2">
          <AgText variant="body" weight="semibold" numberOfLines={2} className="flex-1">
            {consultation.subject}
          </AgText>
          <ConsultationStatusBadge status={consultation.status} />
        </View>

        {consultation.expert ? (
          <AgText variant="caption" color="muted" numberOfLines={1}>
            {consultation.expert.fullName}
          </AgText>
        ) : (
          <AgText variant="caption" color="muted">
            {t('experts.assigningDesk')}
          </AgText>
        )}

        <View className="flex-row flex-wrap items-center gap-1.5">
          <AgBadge
            label={t(
              CATEGORY_LABEL_KEY[consultation.category as ConsultationCategory] ??
                'experts.categoryGeneral',
            )}
            tone="neutral"
          />
          <AgBadge label={t(PRIORITY_LABEL_KEY[priority])} tone={PRIORITY_TONE[priority]} />
          {consultation.crop ? <AgBadge label={consultation.crop} tone="info" /> : null}
        </View>

        <View className="flex-row items-center gap-3">
          <View className="flex-row items-center gap-1">
            <MessagesSquare size={13} color={colors.textMuted} />
            <AgText variant="caption" color="muted">
              {consultation.messageCount}
            </AgText>
          </View>
          {consultation.attachmentCount > 0 ? (
            <View className="flex-row items-center gap-1">
              <Paperclip size={13} color={colors.textMuted} />
              <AgText variant="caption" color="muted">
                {consultation.attachmentCount}
              </AgText>
            </View>
          ) : null}
          <View className="flex-1" />
          <AgText variant="caption" color="muted">
            {t(rt.key, rt.params)}
          </AgText>
        </View>
      </AgCard>
    </AgPressable>
  );
}
