import { CloudOff, TriangleAlert } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';

import { AgButton } from './AgButton';
import { AgText } from './AgText';

interface AgErrorStateProps {
  title?: string;
  message?: string;
  retryLabel?: string;
  onRetry?: () => void;
  offline?: boolean;
  /** Forces readable fixed colors when rendered on a light feature surface. */
  light?: boolean;
}

/** Full-section error with retry — the standard failure surface for queries. */
export function AgErrorState({
  title,
  message,
  retryLabel,
  onRetry,
  offline = false,
  light = false,
}: AgErrorStateProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon = offline ? CloudOff : TriangleAlert;

  return (
    <View className="flex-1 items-center justify-center px-8 py-12">
      <View className="mb-4 h-20 w-20 items-center justify-center rounded-full bg-danger/10">
        <Icon size={34} color={colors.danger} />
      </View>
      <AgText
        variant="headingS"
        weight="semibold"
        center
        style={light ? { color: '#173B2B' } : undefined}
      >
        {title ?? (offline ? t('common.offline') : t('common.somethingWrong'))}
      </AgText>
      {message ? (
        <AgText
          variant="body"
          color={light ? undefined : "muted"}
          center
          className="mt-2"
          style={light ? { color: '#5B6A64' } : undefined}
        >
          {message}
        </AgText>
      ) : null}
      {onRetry ? (
        <AgButton
          light={light}
          title={retryLabel ?? t('common.retry')}
          onPress={onRetry}
          variant="secondary"
          fullWidth={false}
          className="mt-5"
        />
      ) : null}
    </View>
  );
}
