import { ShieldAlert } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import { AgEmptyState, AgScreen } from '@/components/ui';

/** Shown when the caller is not an admin, is suspended, or lacks a permission. */
export function AccessDenied({ message }: { message?: string }) {
  const { t } = useTranslation();
  return (
    <AgScreen>
      <AgEmptyState
        icon={ShieldAlert}
        title={t('admin.accessDeniedTitle')}
        message={message ?? t('admin.accessDeniedMessage')}
      />
    </AgScreen>
  );
}
