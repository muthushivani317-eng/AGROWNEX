import {
  Check,
  Droplets,
  Eye,
  FlaskConical,
  type LucideIcon,
  SprayCan,
  Sprout,
  ThermometerSun,
  Waves,
} from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';

import { AgCard, AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { DashboardTask, TaskIcon, TaskTone } from '../types';

const TASK_ICON: Record<TaskIcon, LucideIcon> = {
  irrigate: Droplets,
  inspect: Eye,
  spray: SprayCan,
  weed: Sprout,
  fertilizer: FlaskConical,
  drainage: Waves,
  heat: ThermometerSun,
};

/** Rule-based checklist for today. Checking off is local/ephemeral. */
export function TodaysTasks({ tasks }: { tasks: DashboardTask[] }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [done, setDone] = useState<Set<string>>(new Set());

  const toneColor = (tone: TaskTone): string =>
    tone === 'primary'
      ? colors.primary
      : tone === 'warning'
        ? colors.warning
        : tone === 'danger'
          ? colors.danger
          : colors.info;

  const toggle = (id: string) =>
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const doneCount = tasks.filter((task) => done.has(task.id)).length;

  return (
    <View>
      <View style={styles.headingRow}>
        <AgText variant="bodyLarge" weight="bold" style={styles.headingText}>
          {t('home.todaysTasks')}
        </AgText>
        {tasks.length ? (
          <AgText variant="bodySmall" weight="semibold" style={styles.progressPill}>
            {t('home.tasksProgress', { done: doneCount, total: tasks.length })}
          </AgText>
        ) : null}
      </View>

      <AgCard variant="elevated" style={styles.card}>
        {tasks.length ? (
          tasks.map((task, index) => {
            const Icon = TASK_ICON[task.icon];
            const isDone = done.has(task.id);
            return (
              <AgPressable
                key={task.id}
                onPress={() => toggle(task.id)}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: isDone }}
                accessibilityLabel={t(task.labelKey)}
                style={[
                  styles.taskPressable,
                  index < tasks.length - 1 && { borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth },
                ]}
              >
                <View style={styles.taskRow}>
                  <View style={[styles.checkbox, { borderColor: isDone ? colors.primary : colors.textDisabled, backgroundColor: isDone ? colors.primary : 'transparent' }]}>
                    {isDone ? <Check size={16} color={colors.onPrimary} strokeWidth={3} /> : null}
                  </View>
                  <View style={[styles.iconTile, { backgroundColor: `${colors.primary}10` }]}>
                    <Icon size={19} color={toneColor(task.tone)} />
                  </View>
                  <AgText
                    variant="body"
                    weight="medium"
                    style={[styles.taskText, isDone && styles.completedText]}
                    numberOfLines={3}
                  >
                    {t(task.labelKey)}
                  </AgText>
                </View>
              </AgPressable>
            );
          })
        ) : (
          <AgText variant="body" center className="py-3" style={styles.mutedText}>
            {t('home.noTasks')}
          </AgText>
        )}
      </AgCard>
    </View>
  );
}

const styles = StyleSheet.create({
  headingRow: { marginBottom: 9, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  headingText: { color: '#173B2B' },
  progressPill: { color: '#165B33', minHeight: 34, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 17, borderWidth: 1, borderColor: '#A9C3AE', backgroundColor: '#FFFDF8', overflow: 'hidden' },
  card: { paddingVertical: 3, paddingHorizontal: 13, borderRadius: 17, backgroundColor: '#FFFDF8', borderColor: '#DED9CA' },
  taskPressable: { width: '100%', minHeight: 70, justifyContent: 'center', paddingVertical: 7 },
  taskRow: { width: '100%', minHeight: 56, flexDirection: 'row', alignItems: 'center', gap: 11 },
  checkbox: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  iconTile: { width: 38, height: 38, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
  taskText: { flex: 1, minWidth: 0, color: '#173B2B', lineHeight: 22 },
  completedText: { textDecorationLine: 'line-through', opacity: 0.6 },
  mutedText: { color: '#58685F' },
});
