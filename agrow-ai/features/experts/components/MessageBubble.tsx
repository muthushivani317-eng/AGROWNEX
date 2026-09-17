import { Info } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Image, Pressable, View } from 'react-native';

import { AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { ConsultationAttachment, ConsultationMessage } from '../types';
import { relativeTimeKey } from '../utils/time';

interface Props {
  message: ConsultationMessage;
  onOpenAttachment: (attachment: ConsultationAttachment) => void;
}

/** One entry in the immutable conversation timeline. Farmer messages align right;
 * expert messages left; system notes are centered and muted. */
export function MessageBubble({ message, onOpenAttachment }: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const rt = relativeTimeKey(message.createdAt);

  if (message.isSystem) {
    return (
      <View className="my-1 flex-row items-center justify-center gap-1.5 px-6">
        <Info size={13} color={colors.textMuted} />
        <AgText variant="caption" color="muted" className="text-center">
          {message.body}
        </AgText>
      </View>
    );
  }

  const isFarmer = message.senderType === 'farmer';
  return (
    <View className={isFarmer ? 'items-end' : 'items-start'}>
      <View
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 ${
          isFarmer ? 'rounded-br-md bg-primary' : 'rounded-bl-md bg-surface-card'
        }`}
      >
        {!isFarmer ? (
          <AgText variant="caption" weight="semibold" color="primary" className="mb-0.5">
            {t('experts.expert')}
          </AgText>
        ) : null}
        <AgText variant="body" color={isFarmer ? 'onPrimary' : 'default'}>
          {message.body}
        </AgText>
        {message.attachments.length > 0 ? (
          <View className="mt-2 flex-row flex-wrap gap-2">
            {message.attachments.map((att) => (
              <Pressable
                key={att.id}
                onPress={() => onOpenAttachment(att)}
                accessibilityRole="imagebutton"
                accessibilityLabel={att.caption ?? t('experts.attachment')}
              >
                <Image
                  source={{ uri: att.thumbnailUrl ?? att.fileUrl }}
                  className="h-20 w-20 rounded-lg"
                  resizeMode="cover"
                />
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>
      <AgText variant="caption" color="muted" className="mx-1 mt-0.5">
        {t(rt.key, rt.params)}
      </AgText>
    </View>
  );
}
