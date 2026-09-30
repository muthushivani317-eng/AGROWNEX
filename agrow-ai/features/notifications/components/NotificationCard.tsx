import { ChevronRight } from 'lucide-react-native';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';

import { MODULE_LABEL_KEY, SEVERITY_LABEL_KEY } from '../constants';
import type { NotificationItem } from '../types';
import { isValidActionRoute } from '../utils/priority';
import { relativeTimeKey } from '../utils/time';
import { MODULE_ICON } from './moduleIcon';
import { notificationTheme as nt } from '../notificationTheme';

interface Props { item: NotificationItem; onPress: (item: NotificationItem) => void }

const severityColor = { info: nt.info, warning: nt.warning, critical: nt.critical };
const severitySoft = { info: nt.infoSoft, warning: nt.warningSoft, critical: nt.criticalSoft };

/** Memoized list card backed entirely by real notification model fields. */
export const NotificationCard = memo(function NotificationCard({ item, onPress }: Props) {
  const { t } = useTranslation();
  const Icon = MODULE_ICON[item.module];
  const rt = relativeTimeKey(item.createdAt);
  const color = severityColor[item.severity];
  const hasAction = isValidActionRoute(item.actionRoute);

  return (
    <AgPressable
      onPress={() => onPress(item)}
      accessibilityRole="button"
      accessibilityLabel={t(item.titleKey, item.payload)}
      accessibilityState={{ selected: item.read }}
      style={({ pressed }) => [styles.card, !item.read && styles.unreadCard, pressed && styles.pressed]}
    >
      <View style={[styles.severityRail, { backgroundColor: color }]} />
      <View style={[styles.iconTile, { borderColor: `${color}55`, backgroundColor: severitySoft[item.severity] }]}>
        <Icon size={28} color={color} />
      </View>
      <View style={styles.copy}>
        <View style={[styles.badge, { backgroundColor: severitySoft[item.severity] }]}>
          <AgText variant="caption" weight="semibold" style={{ color }}>{t(SEVERITY_LABEL_KEY[item.severity])}</AgText>
        </View>
        <View style={styles.titleRow}>
          <AgText variant="bodyLarge" weight="bold" numberOfLines={3} style={[styles.primaryText, { flex: 1, minWidth: 0 }]}>{t(item.titleKey, item.payload)}</AgText>
          {!item.read ? <View style={styles.unreadDot} accessibilityLabel={t('notifications.unreadDot')} /> : null}
        </View>
        <AgText variant="bodySmall" numberOfLines={3} style={styles.secondaryText}>{t(item.messageKey, item.payload)}</AgText>
        {item.module === 'schemes' ? (
          <AgText variant="caption" weight="semibold" style={styles.schemeWarning}>{t('notifications.schemeVerifyWarning')}</AgText>
        ) : null}
        <View style={styles.metaRow}>
          <AgText variant="caption" style={styles.secondaryText}>{t(MODULE_LABEL_KEY[item.module])}</AgText>
          <View style={styles.metaDot} />
          <AgText variant="caption" style={styles.secondaryText}>{t(rt.key, rt.params)}</AgText>
        </View>
      </View>
      {hasAction ? <View style={styles.action}><ChevronRight size={22} color={nt.primary} /></View> : null}
    </AgPressable>
  );
});

const styles = StyleSheet.create({
  card: { minHeight: 148, flexDirection: 'row', alignItems: 'center', gap: 13, padding: 16, overflow: 'hidden', borderRadius: 22, borderWidth: 1, borderColor: nt.border, backgroundColor: nt.surface },
  unreadCard: { borderColor: '#8EC49B', backgroundColor: '#FBFFF8' },
  severityRail: { position: 'absolute', left: 0, top: 0, bottom: 0, width: 5 },
  pressed: { opacity: 0.8 },
  iconTile: { width: 52, height: 52, alignItems: 'center', justifyContent: 'center', borderRadius: 25, borderWidth: 1 },
  copy: { flex: 1, minWidth: 0, alignItems: 'flex-start', gap: 6 },
  badge: { alignSelf: 'flex-start', paddingHorizontal: 9, paddingVertical: 4, borderRadius: 8 },
  titleRow: { width: '100%', flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  primaryText: { flex: 1, color: nt.ink },
  secondaryText: { color: nt.muted },
  unreadDot: { width: 10, height: 10, marginTop: 6, borderRadius: 5, backgroundColor: nt.primary },
  schemeWarning: { color: nt.warning },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 9 },
  metaDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: nt.primary },
  action: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center', borderRadius: 14, backgroundColor: nt.primarySoft },
});
