import { FlaskConical } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import { AgCard, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

/** Honest banner shown whenever the local sample dataset is being displayed. */
export function SampleNotice({ visible }: { visible: boolean }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  if (!visible) return null;
  return (
    <AgCard className="flex-row items-center gap-2 border border-info/30 bg-info/5">
      <FlaskConical size={16} color={colors.info} />
      <AgText variant="caption" color="muted" className="flex-1">
        {t('admin.sampleNotice')}
      </AgText>
    </AgCard>
  );
}
