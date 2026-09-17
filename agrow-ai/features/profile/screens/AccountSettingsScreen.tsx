import { useRouter } from 'expo-router';
import {
  ArrowLeft,
  Bell,
  Building2,
  ChevronRight,
  Hash,
  Languages,
  LogOut,
  Mail,
  Mic,
  Palette,
  Phone,
  Ruler,
  Sun,
  Trash2,
} from 'lucide-react-native';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Switch, View } from 'react-native';

import { AgLanguageToggle } from '@/components/AgLanguageToggle';
import { AgThemeToggle } from '@/components/AgThemeToggle';
import {
  AgButton,
  AgCard,
  AgChip,
  AgPressable,
  AgScreen,
  AgSpinner,
  AgText,
} from '@/components/ui';
import { useAuth, useCloseAccount, useLogout } from '@/features/auth';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useThemeStore } from '@/stores/themeStore';
import { formatIndianPhone } from '@/utils/format';

import { UNIT_OPTIONS } from '../constants';
import { ProfileInfoRow } from '../components/ProfileInfoRow';
import { ProfileSection } from '../components/ProfileSection';
import { usePreferences, useUpdatePreferences } from '../hooks/usePreferences';

function ToggleRow({
  icon,
  label,
  description,
  value,
  disabled,
  onValueChange,
}: {
  icon: ReactNode;
  label: string;
  description: string;
  value: boolean;
  disabled?: boolean;
  onValueChange: (next: boolean) => void;
}) {
  const { colors } = useAppTheme();
  return (
    <View className="flex-row items-center gap-3">
      <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
        {icon}
      </View>
      <View className="flex-1">
        <AgText variant="body" weight="medium">
          {label}
        </AgText>
        <AgText variant="caption" color="muted">
          {description}
        </AgText>
      </View>
      <Switch
        value={value}
        disabled={disabled}
        onValueChange={onValueChange}
        trackColor={{ true: colors.primary, false: colors.border }}
        thumbColor={colors.surface}
        accessibilityLabel={label}
      />
    </View>
  );
}

export function AccountSettingsScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const sunlightEnabled = useThemeStore((state) => state.sunlightEnabled);
  const setSunlightEnabled = useThemeStore(
    (state) => state.setSunlightEnabled,
  );
  const { user } = useAuth();
  const logout = useLogout();
  const closeAccount = useCloseAccount();

  const { data: prefs, isLoading } = usePreferences();
  const updatePrefs = useUpdatePreferences();

  const confirmLogout = () => {
    Alert.alert(t('common.logout'), '', [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.logout'),
        style: 'destructive',
        onPress: () => logout.mutate(),
      },
    ]);
  };

  const confirmCloseAccount = () => {
    Alert.alert(
      t('profile.closeAccount'),
      t('profile.closeAccountWarning'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('profile.closeAccountConfirm'),
          style: 'destructive',
          onPress: () => closeAccount.mutate(),
        },
      ],
    );
  };

  return (
    <AgScreen scroll>
      <View className="mt-2 flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="-ml-2 h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('profile.accountSettings')}
        </AgText>
      </View>

      {/* Account (read-only contact) */}
      <ProfileSection title={t('profile.account')}>
        <ProfileInfoRow
          icon={<Phone size={18} color={colors.primary} />}
          label={t('profile.phone')}
          value={user?.phone ? formatIndianPhone(user.phone) : null}
        />
        <ProfileInfoRow
          icon={<Mail size={18} color={colors.primary} />}
          label={t('profile.email')}
          value={user?.email}
        />
        <ProfileInfoRow
          icon={<Hash size={18} color={colors.primary} />}
          label={t('profile.farmerCode')}
          value={user?.farmerRef}
        />
      </ProfileSection>

      {/* FPOs/organizations this farmer has approved to see their data */}
      <ProfileSection title={t('profile.linkedOrganizations')}>
        <AgPressable
          onPress={() => router.push('/profile/organizations')}
          className="flex-row items-center gap-3"
          accessibilityRole="button"
          accessibilityLabel={t('profile.linkedOrganizations')}
        >
          <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <Building2 size={18} color={colors.primary} />
          </View>
          <View className="flex-1">
            <AgText variant="body" weight="medium">
              {t('profile.linkedOrganizations')}
            </AgText>
            <AgText variant="caption" color="muted">
              {t('profile.linkedOrganizationsDesc')}
            </AgText>
          </View>
          <ChevronRight size={18} color={colors.textMuted} />
        </AgPressable>
      </ProfileSection>

      {/* Appearance & language (reuse existing controls) */}
      <ProfileSection title={t('settings.appearance')}>
        <View className="flex-row items-center gap-3">
          <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <Palette size={18} color={colors.primary} />
          </View>
          <View className="flex-1">
            <AgText variant="body" weight="medium" className="mb-2">
              {t('settings.appearance')}
            </AgText>
            <AgThemeToggle />
          </View>
        </View>
        <ToggleRow
          icon={<Sun size={18} color={colors.primary} />}
          label={t('settings.sunlightMode')}
          description={t('settings.sunlightModeDesc')}
          value={sunlightEnabled}
          onValueChange={setSunlightEnabled}
        />
        <View className="flex-row items-center gap-3">
          <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
            <Languages size={18} color={colors.primary} />
          </View>
          <View className="flex-1">
            <AgText variant="body" weight="medium" className="mb-2">
              {t('settings.language')}
            </AgText>
            <AgLanguageToggle className="self-start" />
          </View>
        </View>
      </ProfileSection>

      {/* Preferences (persisted via /farmers/preferences) */}
      <ProfileSection title={t('profile.preferences')}>
        {isLoading || !prefs ? (
          <AgSpinner />
        ) : (
          <>
            <ToggleRow
              icon={<Bell size={18} color={colors.primary} />}
              label={t('profile.notifications')}
              description={t('profile.notificationsDesc')}
              value={prefs.notificationsEnabled}
              disabled={updatePrefs.isPending}
              onValueChange={(v) =>
                updatePrefs.mutate({ notificationsEnabled: v })
              }
            />
            <ToggleRow
              icon={<Mic size={18} color={colors.primary} />}
              label={t('profile.voice')}
              description={t('profile.voiceDesc')}
              value={prefs.voiceEnabled}
              disabled={updatePrefs.isPending}
              onValueChange={(v) => updatePrefs.mutate({ voiceEnabled: v })}
            />
            <View className="flex-row items-start gap-3">
              <View className="h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                <Ruler size={18} color={colors.primary} />
              </View>
              <View className="flex-1">
                <AgText variant="body" weight="medium" className="mb-2">
                  {t('profile.units')}
                </AgText>
                <View className="flex-row gap-2">
                  {UNIT_OPTIONS.map((opt) => (
                    <AgChip
                      key={opt.value}
                      label={t(opt.labelKey)}
                      selected={prefs.preferredUnits === opt.value}
                      onPress={() =>
                        updatePrefs.mutate({ preferredUnits: opt.value })
                      }
                    />
                  ))}
                </View>
              </View>
            </View>
          </>
        )}
      </ProfileSection>

      <AgButton
        variant="danger"
        title={t('common.logout')}
        onPress={confirmLogout}
        loading={logout.isPending}
        leftIcon={<LogOut size={20} color="#fff" />}
        className="mt-8"
      />
      <AgButton
        variant="danger"
        title={t('profile.closeAccount')}
        onPress={confirmCloseAccount}
        loading={closeAccount.isPending}
        leftIcon={<Trash2 size={20} color="#fff" />}
        className="mt-3"
      />
      {closeAccount.isError ? (
        <AgText variant="caption" color="danger" className="mt-2 text-center">
          {t('profile.closeAccountFailed')}
        </AgText>
      ) : null}
    </AgScreen>
  );
}
