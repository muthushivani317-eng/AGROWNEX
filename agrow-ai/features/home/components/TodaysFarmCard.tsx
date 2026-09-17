import { ChevronRight, CirclePlus, Home, MapPin, Ruler, Sprout } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';

import { AgButton, AgCard, AgPressable, AgText } from '@/components/ui';
import type { FarmSummary } from '@/features/farm';
import { hectaresToAcres } from '@/features/farm/utils/geo';
import { cropLabel } from '@/features/farm/utils/labels';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

import { relativeTimeKey } from '../utils/time';

function Stat({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.stat}>
      <View style={styles.statLabel}>
        {icon}
        <AgText variant="caption" style={styles.mutedText}>
          {label}
        </AgText>
      </View>
      <AgText variant="bodySmall" weight="semibold" numberOfLines={3} style={[styles.statValue, styles.primaryText]}>
        {value}
      </AgText>
    </View>
  );
}

export function TodaysFarmCard({
  farm,
  onPress,
  onRegister,
}: {
  farm: FarmSummary | null;
  onPress: () => void;
  onRegister: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { isTamil } = useLanguage();

  if (!farm) {
    return (
      <AgCard variant="elevated" style={[styles.emptyCard, styles.lightCard]}>
        <View style={styles.emptyCopy}>
          <AgText variant="headingS" weight="bold" style={styles.primaryText}>{t('home.noFarmTitle')}</AgText>
          <AgText variant="body" style={[styles.emptyMessage, styles.mutedText]}>{t('home.noFarmMessage')}</AgText>
          <AgButton
            title={t('farm.addFarm')}
            size="md"
            fullWidth={false}
            className="mt-3"
            onPress={onRegister}
            rightIcon={<CirclePlus size={21} color={colors.onPrimary} />}
          />
        </View>
        <View style={[styles.illustration, { backgroundColor: `${colors.primary}0D` }]}>
          <Home size={48} color={colors.primary} strokeWidth={1.5} />
          <View style={[styles.fieldLine, { backgroundColor: colors.primary }]} />
        </View>
      </AgCard>
    );
  }

  const crop = cropLabel(farm.crop, isTamil) ?? '—';
  const area =
    farm.areaHectares != null
      ? `${farm.areaHectares.toFixed(2)} ${t('farm.hectaresShort')} · ${hectaresToAcres(farm.areaHectares).toFixed(2)} ${t('farm.acresShort')}`
      : t('farm.noArea');
  const location = farm.district ?? t('farm.noLocation');
  const updated = relativeTimeKey(farm.updatedAt);

  return (
    <AgPressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={farm.name}
    >
      <AgCard variant="elevated" style={[styles.farmCard, styles.lightCard]}>
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <AgText variant="label" weight="medium" style={styles.mutedText}>
              {t('home.todaysFarm')}
            </AgText>
            <AgText variant="headingS" weight="bold" numberOfLines={2} style={[styles.name, styles.primaryText]}>
              {farm.name}
            </AgText>
          </View>
          <View style={[styles.openButton, { backgroundColor: `${colors.primary}12` }]}>
            <ChevronRight size={20} color={colors.primary} />
          </View>
        </View>

        <View style={[styles.detailsPanel, { backgroundColor: '#F8F6EE', borderColor: '#DED9CA' }]}>
          <View style={styles.detailsRow}>
            <Stat
              icon={<Sprout size={14} color={colors.primary} />}
              label={t('farm.crop')}
              value={crop}
            />
            <View style={[styles.verticalDivider, { backgroundColor: colors.border }]} />
            <Stat
              icon={<Ruler size={14} color={colors.primary} />}
              label={t('farm.area')}
              value={area}
            />
          </View>
          <View style={[styles.horizontalDivider, { backgroundColor: colors.border }]} />
          <Stat
            icon={<MapPin size={14} color={colors.primary} />}
            label={t('farm.location')}
            value={location}
          />
        </View>

        <AgText variant="caption" style={[styles.updated, styles.mutedText]}>
          {t('home.lastUpdated')} · {t(updated.key, updated.params)}
        </AgText>
      </AgCard>
    </AgPressable>
  );
}

const styles = StyleSheet.create({
  lightCard: { backgroundColor: '#FFFDF8', borderColor: '#DED9CA' },
  primaryText: { color: '#173B2B' },
  mutedText: { color: '#58685F' },
  emptyCard: { minHeight: 160, flexDirection: 'row', alignItems: 'center', gap: 14 },
  emptyCopy: { flex: 1, minWidth: 0 },
  emptyMessage: { marginTop: 7 },
  illustration: {
    width: 116, height: 116, borderRadius: 58, overflow: 'hidden',
    alignItems: 'center', justifyContent: 'center',
  },
  fieldLine: { position: 'absolute', bottom: 25, width: 82, height: 5, borderRadius: 3, opacity: 0.45 },
  farmCard: { padding: 15, borderRadius: 17 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  headerCopy: { flex: 1, minWidth: 0 },
  name: { marginTop: 2 },
  openButton: { width: 40, height: 40, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  detailsPanel: { marginTop: 12, borderRadius: 13, borderWidth: 1, padding: 12 },
  detailsRow: { flexDirection: 'row', alignItems: 'stretch', gap: 12 },
  stat: { flex: 1, minWidth: 0 },
  statLabel: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 5 },
  statValue: { lineHeight: 20 },
  verticalDivider: { width: 1 },
  horizontalDivider: { height: 1, marginVertical: 13 },
  updated: { marginTop: 13 },
});
