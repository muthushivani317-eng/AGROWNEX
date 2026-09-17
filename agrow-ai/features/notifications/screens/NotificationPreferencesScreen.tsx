import { useTranslation } from 'react-i18next';
import { Switch, View } from 'react-native';

import { AgCard, AgDropdown, AgScreen, AgSkeleton, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { NotificationBackHeader } from '../components/NotificationBackHeader';
import { MODULE_ICON } from '../components/moduleIcon';
import {
  CHANNEL_PREFERENCE_FIELDS,
  MODULE_LABEL_KEY,
  MODULE_PREFERENCE_FIELDS,
  SEVERITIES,
  SEVERITY_LABEL_KEY,
} from '../constants';
import {
  useNotificationPreferences,
  useUpdatePreferences,
} from '../hooks/useNotifications';
import type { NotificationPreferences, Severity } from '../types';
import { notificationTheme as nt } from '../notificationTheme';

/** Preferences: per-module opt-outs, delivery channels and the min-severity gate. */
export function NotificationPreferencesScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const query = useNotificationPreferences();
  const update = useUpdatePreferences();
  const prefs = query.data;

  const setField = (patch: Partial<NotificationPreferences>) => update.mutate(patch);

  return (
    <AgScreen scroll backgroundColor={nt.background}>
      <NotificationBackHeader title={t('notifications.preferences')} />

      {!prefs ? (
        <View className="mt-4 gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} className="h-28 w-full rounded-card" />
          ))}
        </View>
      ) : (
        <View className="mt-4 gap-5">
          {/* Minimum severity */}
          <View className="gap-2">
            <AgText variant="label" weight="semibold" color="muted">
              {t('notifications.minSeverity')}
            </AgText>
            <AgDropdown
              placeholder={t('notifications.minSeverity')}
              value={prefs.minSeverity}
              options={SEVERITIES.map((s) => ({
                value: s,
                label: t(SEVERITY_LABEL_KEY[s]),
              }))}
              onChange={(value) => setField({ minSeverity: value as Severity })}
            />
            <AgText variant="caption" color="muted">
              {t('notifications.minSeverityHint')}
            </AgText>
          </View>

          {/* Per-module toggles */}
          <View className="gap-2">
            <AgText variant="label" weight="semibold" color="muted">
              {t('notifications.modules')}
            </AgText>
            <AgCard className="gap-1 py-1">
              {MODULE_PREFERENCE_FIELDS.map(({ module, field }) => {
                const Icon = MODULE_ICON[module];
                return (
                  <View
                    key={module}
                    className="flex-row items-center gap-3 py-2.5"
                  >
                    <View className="h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                      <Icon size={16} color={colors.primary} />
                    </View>
                    <AgText variant="body" className="flex-1">
                      {t(MODULE_LABEL_KEY[module])}
                    </AgText>
                    <Switch
                      value={prefs[field]}
                      onValueChange={(v) => setField({ [field]: v })}
                      trackColor={{ true: colors.primary, false: colors.border }}
                      thumbColor={colors.surface}
                      accessibilityLabel={t(MODULE_LABEL_KEY[module])}
                    />
                  </View>
                );
              })}
            </AgCard>
          </View>

          {/* Delivery channels */}
          <View className="gap-2">
            <AgText variant="label" weight="semibold" color="muted">
              {t('notifications.channels')}
            </AgText>
            <AgCard className="gap-1 py-1">
              <View className="flex-row items-center gap-3 py-2.5">
                <AgText variant="body" className="flex-1">
                  {t('notifications.channelInApp')}
                </AgText>
                <AgText variant="caption" color="muted">
                  {t('notifications.channelAlwaysOn')}
                </AgText>
              </View>
              {CHANNEL_PREFERENCE_FIELDS.map(({ field, labelKey }) => (
                <View key={field} className="flex-row items-center gap-3 py-2.5">
                  <AgText variant="body" className="flex-1">
                    {t(labelKey)}
                  </AgText>
                  <Switch
                    value={prefs[field]}
                    onValueChange={(v) => setField({ [field]: v })}
                    trackColor={{ true: colors.primary, false: colors.border }}
                    thumbColor={colors.surface}
                    accessibilityLabel={t(labelKey)}
                  />
                </View>
              ))}
            </AgCard>
            <AgText variant="caption" color="muted">
              {t('notifications.channelsHint')}
            </AgText>
          </View>
        </View>
      )}
    </AgScreen>
  );
}
