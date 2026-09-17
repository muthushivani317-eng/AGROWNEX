import { AlertTriangle, CircleAlert, Grid2X2, Info } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { ScrollView, StyleSheet, View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';

import { FILTERABLE_MODULES, MODULE_LABEL_KEY, SEVERITIES, SEVERITY_LABEL_KEY } from '../constants';
import type { NotificationModuleKey, Severity } from '../types';
import { notificationTheme as nt } from '../notificationTheme';

interface Props {
  module: NotificationModuleKey | null;
  severity: Severity | null;
  counts: Record<'all' | Severity, number>;
  onModule: (m: NotificationModuleKey | null) => void;
  onSeverity: (s: Severity | null) => void;
}

const severityIcon = { info: Info, warning: AlertTriangle, critical: CircleAlert };
const severityColor = { info: nt.info, warning: nt.warning, critical: nt.critical };

/** Filters only by fields present in the notification domain model. */
export function NotificationFilters({ module, severity, counts, onModule, onSeverity }: Props) {
  const { t } = useTranslation();
  const options: Array<{ value: Severity | null; label: string; count: number }> = [
    { value: null, label: t('notifications.filterAll'), count: counts.all },
    ...SEVERITIES.map((value) => ({ value, label: t(SEVERITY_LABEL_KEY[value]), count: counts[value] })),
  ];

  return (
    <View style={styles.group}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {options.map((option) => {
          const selected = severity === option.value;
          const Icon = option.value ? severityIcon[option.value] : Grid2X2;
          const color = option.value ? severityColor[option.value] : nt.primary;
          return (
            <AgPressable
              key={option.value ?? 'all'}
              onPress={() => onSeverity(option.value)}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              style={[styles.severityPill, selected && styles.selectedPill]}
            >
              <Icon size={19} color={color} />
              <AgText variant="bodySmall" weight="semibold" style={styles.text}>{option.label}</AgText>
              <View style={styles.countBadge}><AgText variant="caption" weight="bold" style={styles.text}>{option.count}</AgText></View>
            </AgPressable>
          );
        })}
      </ScrollView>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        <ModulePill label={t('notifications.filterAll')} selected={module === null} onPress={() => onModule(null)} />
        {FILTERABLE_MODULES.map((value) => (
          <ModulePill key={value} label={t(MODULE_LABEL_KEY[value])} selected={module === value} onPress={() => onModule(module === value ? null : value)} />
        ))}
      </ScrollView>
    </View>
  );
}

function ModulePill({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <AgPressable onPress={onPress} accessibilityRole="tab" accessibilityState={{ selected }} style={[styles.modulePill, selected && styles.moduleSelected]}>
      <AgText variant="caption" weight="semibold" style={{ color: selected ? nt.primary : nt.muted }}>{label}</AgText>
    </AgPressable>
  );
}

const styles = StyleSheet.create({
  group: { gap: 10 },
  row: { gap: 10, paddingRight: 18 },
  severityPill: { minHeight: 52, flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 14, borderRadius: 16, borderWidth: 1, borderColor: nt.border, backgroundColor: nt.surface },
  selectedPill: { borderColor: nt.primary, backgroundColor: nt.primarySoft },
  countBadge: { minWidth: 27, height: 27, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 7, borderRadius: 14, backgroundColor: '#DCEBD9' },
  text: { color: nt.ink },
  modulePill: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 14, borderRadius: 14, borderWidth: 1, borderColor: nt.border, backgroundColor: nt.surface },
  moduleSelected: { borderColor: nt.primary, backgroundColor: nt.primarySoft },
});
