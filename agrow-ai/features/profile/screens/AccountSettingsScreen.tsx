import * as Location from 'expo-location';
import { useFocusEffect, useRouter } from 'expo-router';
import {
  ArrowLeft,
  Bell,
  Building2,
  ChevronRight,
  Hash,
  FileText,
  Headphones,
  Languages,
  Leaf,
  LogOut,
  Mail,
  MapPin,
  Mic,
  Moon,
  Palette,
  Pencil,
  Phone,
  Ruler,
  ShieldCheck,
  Smartphone,
  Sprout,
  Sun,
  SunMedium,
  Trash2,
  Users,
  type LucideIcon,
} from 'lucide-react-native';
import { useCallback, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActivityIndicator,
  Alert,
  Linking,
  StyleSheet,
  Switch,
  TouchableOpacity,
  View,
} from 'react-native';

import { AgLanguageToggle } from '@/components/AgLanguageToggle';
import { AgAvatar, AgChip, AgScreen, AgText } from '@/components/ui';
import { useAuth, useCloseAccount, useLogout } from '@/features/auth';
import { useMyPartnerLinks, type PartnerLinkRequest } from '@/features/partnerLinks';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useThemeStore, type ThemePreference } from '@/stores/themeStore';
import type { Palette as ThemePalette } from '@/theme';
import { formatIndianPhone } from '@/utils/format';

import { UNIT_OPTIONS } from '../constants';
import { usePreferences, useUpdatePreferences } from '../hooks/usePreferences';
import { useProfile } from '../hooks/useProfile';

/*
 * Layout rules so both Tamil and English fit on a 360dp phone:
 * - every label column is `flex: 1, minWidth: 0` and may wrap (no truncation);
 * - trailing controls (switch, chevron, edit) never shrink;
 * - wide controls (theme, language, units) sit on their own line below the label.
 */

function tint(isDark: boolean) {
  return {
    pale: isDark ? '#1E3324' : '#EEF6EC',
    card: isDark ? '#1C211D' : '#FFFFFF',
    page: isDark ? '#121412' : '#F7F9F4',
    line: isDark ? '#2C352E' : '#E7ECE4',
    dangerPale: isDark ? '#3A1F1F' : '#FDECEC',
  };
}

type Tint = ReturnType<typeof tint>;

function IconBubble({
  icon: Icon,
  colors,
  t,
  size = 44,
  danger,
}: {
  icon: LucideIcon;
  colors: ThemePalette;
  t: Tint;
  size?: number;
  danger?: boolean;
}) {
  return (
    <View
      style={[
        styles.bubble,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: danger ? t.dangerPale : t.pale,
        },
      ]}
    >
      <Icon
        size={Math.round(size * 0.48)}
        color={danger ? colors.danger : colors.primary}
        strokeWidth={2.1}
      />
    </View>
  );
}

function SectionTitle({
  icon: Icon,
  title,
  subtitle,
  colors,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  colors: ThemePalette;
}) {
  return (
    <View style={styles.sectionTitle}>
      <Icon size={24} color={colors.primary} strokeWidth={2.3} />
      <View style={styles.flexText}>
        <AgText variant="headingS" weight="bold">
          {title}
        </AgText>
        <AgText variant="caption" color="muted" style={styles.gapTop}>
          {subtitle}
        </AgText>
      </View>
    </View>
  );
}

/** One settings row: icon, label + description, optional trailing control. */
function Row({
  icon,
  label,
  description,
  trailing,
  below,
  onPress,
  danger,
  divider = true,
  colors,
  t,
}: {
  icon: LucideIcon;
  label: string;
  description?: string;
  trailing?: ReactNode;
  below?: ReactNode;
  onPress?: () => void;
  danger?: boolean;
  divider?: boolean;
  colors: ThemePalette;
  t: Tint;
}) {
  const body = (
    <View style={[styles.row, divider && { borderBottomWidth: 1, borderBottomColor: t.line }]}>
      <View style={styles.rowMain}>
        <IconBubble icon={icon} colors={colors} t={t} size={42} danger={danger} />
        <View style={styles.flexText}>
          <AgText
            variant="body"
            weight="semibold"
            style={danger ? { color: colors.danger } : undefined}
          >
            {label}
          </AgText>
          {description ? (
            <AgText variant="caption" color="muted" style={styles.gapTop}>
              {description}
            </AgText>
          ) : null}
        </View>
        {trailing ? <View style={styles.trailing}>{trailing}</View> : null}
      </View>
      {below ? <View style={styles.below}>{below}</View> : null}
    </View>
  );
  if (!onPress) return body;
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={description ? `${label}. ${description}` : label}
    >
      {body}
    </TouchableOpacity>
  );
}

function InfoLine({
  icon,
  label,
  value,
  divider = true,
  colors,
  t,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  divider?: boolean;
  colors: ThemePalette;
  t: Tint;
}) {
  return (
    <View
      style={[styles.infoLine, divider && { borderBottomWidth: 1, borderBottomColor: t.line }]}
      accessible
      accessibilityLabel={`${label}: ${value}`}
    >
      <IconBubble icon={icon} colors={colors} t={t} size={40} />
      <View style={styles.flexText}>
        <AgText variant="caption" color="muted">
          {label}
        </AgText>
        <AgText variant="bodyLarge" weight="semibold" style={styles.gapTop}>
          {value}
        </AgText>
      </View>
    </View>
  );
}

const PRIVACY_POLICY_URL = 'https://www.agrowai.in/privacy';

const THEME_OPTIONS: { value: ThemePreference; labelKey: string; icon: LucideIcon }[] = [
  { value: 'light', labelKey: 'settings.themeLight', icon: Sun },
  { value: 'dark', labelKey: 'settings.themeDark', icon: Moon },
  { value: 'system', labelKey: 'settings.themeAuto', icon: Smartphone },
];

/** Icon-over-label segments: labels wrap to two lines instead of clipping. */
function ThemeSegments({ colors, t }: { colors: ThemePalette; t: Tint }) {
  const { t: tr } = useTranslation();
  const preference = useThemeStore((s) => s.preference);
  const setPreference = useThemeStore((s) => s.setPreference);
  return (
    <View style={[styles.segments, { borderColor: t.line }]}>
      {THEME_OPTIONS.map(({ value, labelKey, icon: Icon }) => {
        const active = preference === value;
        return (
          <TouchableOpacity
            key={value}
            onPress={() => setPreference(value)}
            activeOpacity={0.75}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            style={[
              styles.segment,
              active && { backgroundColor: t.pale, borderColor: colors.primary },
            ]}
          >
            <Icon size={22} color={active ? colors.primary : colors.textMuted} />
            <AgText
              variant="caption"
              weight="semibold"
              center
              numberOfLines={2}
              style={{ color: active ? colors.primary : colors.textMuted }}
            >
              {tr(labelKey)}
            </AgText>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function orgSummary(
  links: PartnerLinkRequest[] | undefined,
  kind: 'fpo' | 'kvk',
  tr: (key: string, opts?: Record<string, string>) => string,
  fallback: string,
) {
  const mine = (links ?? []).filter((l) => l.organizationKind === kind);
  const active = mine.filter((l) => l.status === 'active').map((l) => l.organizationName);
  if (active.length) return tr('settings.memberOf', { names: active.join(', ') });
  const waiting = mine
    .filter((l) => l.status === 'join_requested' || l.status === 'pending')
    .map((l) => l.organizationName);
  if (waiting.length) return tr('settings.waitingFor', { names: waiting.join(', ') });
  return fallback;
}

export function AccountSettingsScreen() {
  const { t: tr, i18n } = useTranslation();
  const router = useRouter();
  const { colors, isDark } = useAppTheme();
  const t = tint(isDark);
  const sunlightEnabled = useThemeStore((s) => s.sunlightEnabled);
  const setSunlightEnabled = useThemeStore((s) => s.setSunlightEnabled);
  const { user } = useAuth();
  const { data: profile } = useProfile();
  const { data: links } = useMyPartnerLinks();
  const logout = useLogout();
  const closeAccount = useCloseAccount();
  const { data: prefs, isLoading } = usePreferences();
  const updatePrefs = useUpdatePreferences();

  const [locationOn, setLocationOn] = useState<boolean | null>(null);
  useFocusEffect(
    useCallback(() => {
      let alive = true;
      Location.getForegroundPermissionsAsync()
        .then((p) => alive && setLocationOn(p.granted))
        .catch(() => alive && setLocationOn(null));
      return () => {
        alive = false;
      };
    }, []),
  );

  const confirmLogout = () => {
    Alert.alert(tr('common.logout'), '', [
      { text: tr('common.cancel'), style: 'cancel' },
      { text: tr('common.logout'), style: 'destructive', onPress: () => logout.mutate() },
    ]);
  };

  const confirmCloseAccount = () => {
    Alert.alert(tr('profile.closeAccount'), tr('profile.closeAccountWarning'), [
      { text: tr('common.cancel'), style: 'cancel' },
      {
        text: tr('profile.closeAccountConfirm'),
        style: 'destructive',
        onPress: () => closeAccount.mutate(),
      },
    ]);
  };

  const name = profile?.fullName?.trim() || user?.name?.trim() || tr('settings.myAccount');
  const openOrgs = () => router.push('/profile/organizations');
  const chevron = <ChevronRight size={20} color={colors.primary} />;
  const toggle = (value: boolean, onChange: (v: boolean) => void, label: string, disabled?: boolean) => (
    <Switch
      value={value}
      disabled={disabled}
      onValueChange={onChange}
      trackColor={{ true: colors.primary, false: colors.border }}
      thumbColor="#FFFFFF"
      accessibilityLabel={label}
    />
  );

  return (
    <AgScreen scroll backgroundColor={t.page} contentContainerStyle={styles.screen}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={tr('common.back')}
          style={[styles.back, { backgroundColor: t.pale }]}
        >
          <ArrowLeft size={24} color={colors.primary} />
        </TouchableOpacity>
        <AgText variant="headingM" weight="bold" style={styles.flexText}>
          {tr('profile.accountSettings')}
        </AgText>
      </View>

      {/* Account card */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.line }]}>
        <Leaf
          size={120}
          color={colors.primary}
          opacity={0.07}
          style={styles.watermark}
          pointerEvents="none"
        />
        <View style={styles.accountTop}>
          <View style={[styles.avatarRing, { backgroundColor: t.pale }]}>
            <AgAvatar uri={profile?.photoUrl ?? user?.photoUrl} name={name} size={64} light />
          </View>
          <View style={styles.flexText}>
            <AgText variant="headingS" weight="bold" numberOfLines={2}>
              {name}
            </AgText>
            <AgText variant="caption" color="muted" style={styles.gapTop}>
              {tr('settings.myAccountDesc')}
            </AgText>
          </View>
          <TouchableOpacity
            onPress={() => router.push('/profile/edit')}
            accessibilityRole="button"
            accessibilityLabel={tr('common.edit')}
            style={[styles.editPill, { borderColor: colors.primary, backgroundColor: t.pale }]}
          >
            <Pencil size={16} color={colors.primary} />
            <AgText variant="caption" weight="bold" style={{ color: colors.primary }}>
              {tr('common.edit')}
            </AgText>
          </TouchableOpacity>
        </View>
        <InfoLine
          icon={Phone}
          label={tr('profile.phone')}
          value={user?.phone ? formatIndianPhone(user.phone) : '—'}
          colors={colors}
          t={t}
        />
        <InfoLine icon={Mail} label={tr('profile.email')} value={user?.email || '—'} colors={colors} t={t} />
        <InfoLine
          icon={Hash}
          label={tr('profile.farmerCode')}
          value={user?.farmerRef || '—'}
          divider={false}
          colors={colors}
          t={t}
        />
      </View>

      {/* Linked organizations */}
      <SectionTitle
        icon={Users}
        title={tr('profile.linkedOrganizations')}
        subtitle={tr('settings.organizationsDesc')}
        colors={colors}
      />
      {(
        [
          { kind: 'fpo', icon: Building2, title: 'settings.fpoTitle', desc: 'settings.fpoDesc' },
          { kind: 'kvk', icon: Sprout, title: 'settings.kvkTitle', desc: 'settings.kvkDesc' },
        ] as const
      ).map((org) => (
        <TouchableOpacity
          key={org.kind}
          onPress={openOrgs}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel={tr(org.title)}
          style={[styles.card, styles.orgCard, { backgroundColor: t.card, borderColor: t.line }]}
        >
          <IconBubble icon={org.icon} colors={colors} t={t} size={52} />
          <View style={styles.flexText}>
            <AgText variant="body" weight="bold">
              {tr(org.title)}
            </AgText>
            <AgText variant="caption" color="muted" style={styles.gapTop}>
              {orgSummary(links, org.kind, tr, tr(org.desc))}
            </AgText>
          </View>
          <View style={[styles.chevronBubble, { backgroundColor: t.pale }]}>{chevron}</View>
        </TouchableOpacity>
      ))}

      {/* Preferences */}
      <SectionTitle
        icon={Palette}
        title={tr('profile.preferences')}
        subtitle={tr('settings.preferencesDesc')}
        colors={colors}
      />
      <View style={[styles.card, styles.listCard, { backgroundColor: t.card, borderColor: t.line }]}>
        <Row
          icon={SunMedium}
          label={tr('settings.appearance')}
          description={tr('settings.appearanceDesc')}
          below={<ThemeSegments colors={colors} t={t} />}
          colors={colors}
          t={t}
        />
        <Row
          icon={Sun}
          label={tr('settings.sunlightMode')}
          description={tr('settings.sunlightModeDesc')}
          trailing={toggle(sunlightEnabled, setSunlightEnabled, tr('settings.sunlightMode'))}
          colors={colors}
          t={t}
        />
        <Row
          icon={Languages}
          label={tr('settings.language')}
          description={tr('settings.languageDesc')}
          below={<AgLanguageToggle className="self-start" />}
          colors={colors}
          t={t}
        />
        {isLoading || !prefs ? (
          <View style={styles.loading}>
            <ActivityIndicator color={colors.primary} />
          </View>
        ) : (
          <>
            <Row
              icon={Bell}
              label={tr('profile.notifications')}
              description={tr('profile.notificationsDesc')}
              trailing={toggle(
                prefs.notificationsEnabled,
                (v) => updatePrefs.mutate({ notificationsEnabled: v }),
                tr('profile.notifications'),
                updatePrefs.isPending,
              )}
              colors={colors}
              t={t}
            />
            <Row
              icon={Mic}
              label={tr('profile.voice')}
              description={tr('profile.voiceDesc')}
              trailing={toggle(
                prefs.voiceEnabled,
                (v) => updatePrefs.mutate({ voiceEnabled: v }),
                tr('profile.voice'),
                updatePrefs.isPending,
              )}
              colors={colors}
              t={t}
            />
            <Row
              icon={Ruler}
              label={tr('profile.units')}
              below={
                <View style={styles.chips}>
                  {UNIT_OPTIONS.map((opt) => (
                    <AgChip
                      key={opt.value}
                      label={tr(opt.labelKey)}
                      selected={prefs.preferredUnits === opt.value}
                      onPress={() => updatePrefs.mutate({ preferredUnits: opt.value })}
                    />
                  ))}
                </View>
              }
              colors={colors}
              t={t}
            />
          </>
        )}
        <Row
          icon={MapPin}
          label={tr('settings.location')}
          description={
            locationOn == null
              ? tr('settings.locationDesc')
              : `${tr(locationOn ? 'settings.locationOn' : 'settings.locationOff')} · ${tr('settings.locationDesc')}`
          }
          trailing={chevron}
          onPress={() => void Linking.openSettings()}
          divider={false}
          colors={colors}
          t={t}
        />
      </View>

      {/* Security & support */}
      <SectionTitle
        icon={ShieldCheck}
        title={tr('settings.securitySupport')}
        subtitle={tr('settings.securitySupportDesc')}
        colors={colors}
      />
      <View style={[styles.card, styles.listCard, { backgroundColor: t.card, borderColor: t.line }]}>
        <Row
          icon={Headphones}
          label={tr('support.reportIssue')}
          description={tr('support.profileDescription')}
          trailing={chevron}
          onPress={() => router.push('/support' as never)}
          colors={colors}
          t={t}
        />
        <Row
          icon={FileText}
          label={tr('settings.privacyPolicy')}
          description={tr('settings.privacyPolicyDesc')}
          trailing={chevron}
          onPress={() => void Linking.openURL(`${PRIVACY_POLICY_URL}?lang=${i18n.language === 'ta' ? 'ta' : 'en'}`)}
          colors={colors}
          t={t}
        />
        <Row
          icon={LogOut}
          label={tr('common.logout')}
          description={tr('settings.logoutDesc')}
          trailing={logout.isPending ? <ActivityIndicator color={colors.danger} /> : null}
          onPress={confirmLogout}
          danger
          colors={colors}
          t={t}
        />
        <Row
          icon={Trash2}
          label={tr('profile.closeAccount')}
          description={tr('settings.closeAccountDesc')}
          trailing={closeAccount.isPending ? <ActivityIndicator color={colors.danger} /> : null}
          onPress={confirmCloseAccount}
          danger
          divider={false}
          colors={colors}
          t={t}
        />
      </View>
      {closeAccount.isError ? (
        <AgText variant="caption" color="danger" center style={styles.gapTop}>
          {tr('profile.closeAccountFailed')}
        </AgText>
      ) : null}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingTop: 8, paddingBottom: 48 },
  flexText: { flex: 1, minWidth: 0 },
  gapTop: { marginTop: 3 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 18 },
  back: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  card: {
    borderRadius: 22,
    borderWidth: 1,
    padding: 16,
    overflow: 'hidden',
    shadowColor: '#1B3A26',
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  listCard: { paddingVertical: 4 },
  watermark: { position: 'absolute', right: -18, bottom: -18 },
  accountTop: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 8 },
  avatarRing: { width: 76, height: 76, borderRadius: 38, alignItems: 'center', justifyContent: 'center' },
  editPill: {
    flexShrink: 0,
    minHeight: 40,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  infoLine: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 12 },
  bubble: { alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  sectionTitle: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginTop: 26, marginBottom: 12 },
  orgCard: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 12 },
  chevronBubble: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  row: { paddingVertical: 14 },
  rowMain: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  trailing: { flexShrink: 0, marginLeft: 4 },
  below: { marginTop: 12 },
  segments: { flexDirection: 'row', gap: 8, borderWidth: 1, borderRadius: 16, padding: 6 },
  segment: {
    flex: 1,
    minHeight: 76,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingHorizontal: 4,
    paddingVertical: 8,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  loading: { paddingVertical: 18, alignItems: 'center' },
});
