import dayjs from 'dayjs';
import { Calendar, ChevronLeft, ChevronRight, X } from 'lucide-react-native';
import { type ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Modal,
  Pressable,
  StyleSheet,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/useAppTheme';

import { AgText } from './AgText';

const WEEKDAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

interface AgDatePickerProps {
  label?: string;
  placeholder: string;
  /** ISO `YYYY-MM-DD`, or empty string when unset. */
  value?: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  error?: string;
  title?: string;
  leftAccessory?: ReactNode;
  fieldStyle?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
  labelStyle?: StyleProp<TextStyle>;
}

/**
 * Themed calendar date picker that opens a full-screen month grid on tap — no
 * keyboard, no manual typing. Mirrors {@link AgDropdown}'s trigger/modal and the
 * calendar grid used by MonthView, so it stays consistent with the app's
 * farmer-friendly picker style. Stores/emits ISO `YYYY-MM-DD`.
 */
export function AgDatePicker({
  label,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  title,
  leftAccessory,
  fieldStyle,
  textStyle,
  labelStyle,
}: AgDatePickerProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(() =>
    (value ? dayjs(value) : dayjs()).startOf('month'),
  );

  const today = dayjs().format('YYYY-MM-DD');
  const daysInMonth = cursor.daysInMonth();
  const leading = cursor.day();
  const cells: (string | null)[] = [
    ...Array.from({ length: leading }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) =>
      cursor.date(i + 1).format('YYYY-MM-DD'),
    ),
  ];

  const openPicker = () => {
    // Re-anchor the visible month to the current value (or today) on each open,
    // so editing a farm shows the month of its saved sowing date.
    setCursor((value ? dayjs(value) : dayjs()).startOf('month'));
    setOpen(true);
  };

  const close = () => {
    setOpen(false);
    onBlur?.();
  };

  const select = (date: string) => {
    onChange(date);
    setOpen(false);
    onBlur?.();
  };

  return (
    <View style={styles.container}>
      {label ? (
        <AgText variant="label" weight="medium" color="muted" style={[styles.label, labelStyle]}>
          {label}
        </AgText>
      ) : null}

      <Pressable
        onPress={openPicker}
        accessibilityRole="button"
        accessibilityLabel={label ?? placeholder}
        style={[
          styles.trigger,
          {
            borderColor: error ? colors.danger : colors.border,
            backgroundColor: colors.surface,
          },
          fieldStyle,
        ]}
      >
        <View style={styles.triggerContent}>
          {leftAccessory ? <View style={styles.leftAccessory}>{leftAccessory}</View> : null}
          <AgText
            color={value ? 'default' : 'disabled'}
            numberOfLines={1}
            style={[styles.triggerText, textStyle]}
          >
            {value ? dayjs(value).format('DD MMM YYYY') : placeholder}
          </AgText>
        </View>
        <Calendar size={20} color={colors.textMuted} />
      </Pressable>

      {error ? (
        <AgText variant="caption" color="danger" style={styles.error}>
          {error}
        </AgText>
      ) : null}

      <Modal
        visible={open}
        animationType="slide"
        presentationStyle="fullScreen"
        onRequestClose={close}
      >
        <SafeAreaView
          style={[styles.modal, { backgroundColor: colors.bg }]}
          edges={['top', 'bottom']}
        >
          <View style={styles.modalHeader}>
            <AgText variant="headingS" weight="semibold">
              {title ?? placeholder}
            </AgText>
            <Pressable
              onPress={close}
              accessibilityRole="button"
              accessibilityLabel={t('common.close')}
              style={[styles.closeButton, { backgroundColor: colors.card }]}
            >
              <X size={26} color={colors.text} />
            </Pressable>
          </View>

          <View style={styles.calendarBody}>
            <View style={styles.monthRow}>
              <Pressable
                onPress={() => setCursor((c) => c.subtract(1, 'month'))}
                accessibilityRole="button"
                accessibilityLabel={t('calendar.prevMonth')}
                style={styles.monthButton}
              >
                <ChevronLeft size={22} color={colors.text} />
              </Pressable>
              <AgText variant="body" weight="semibold">
                {cursor.format('MMMM YYYY')}
              </AgText>
              <Pressable
                onPress={() => setCursor((c) => c.add(1, 'month'))}
                accessibilityRole="button"
                accessibilityLabel={t('calendar.nextMonth')}
                style={styles.monthButton}
              >
                <ChevronRight size={22} color={colors.text} />
              </Pressable>
            </View>

            <View style={styles.weekdayRow}>
              {WEEKDAYS.map((d) => (
                <View key={d} style={styles.weekdayCell}>
                  <AgText variant="caption" color="muted">
                    {d}
                  </AgText>
                </View>
              ))}
            </View>

            <View style={styles.grid}>
              {cells.map((date, i) => {
                if (!date) {
                  return (
                    <View
                      key={`b${i}`}
                      style={[styles.dayCell, { width: `${100 / 7}%` }]}
                    />
                  );
                }
                const isSelected = date === value;
                const isToday = date === today;
                return (
                  <View
                    key={date}
                    style={[styles.dayCell, { width: `${100 / 7}%` }]}
                  >
                    <Pressable
                      onPress={() => select(date)}
                      accessibilityRole="button"
                      accessibilityState={{ selected: isSelected }}
                      accessibilityLabel={dayjs(date).format('DD MMMM YYYY')}
                      style={[
                        styles.dayButton,
                        {
                          backgroundColor: isSelected
                            ? colors.primary
                            : isToday
                              ? `${colors.primary}1A`
                              : 'transparent',
                        },
                      ]}
                    >
                      <AgText
                        variant="bodySmall"
                        weight={isToday || isSelected ? 'bold' : 'regular'}
                        style={{ color: isSelected ? colors.onPrimary : colors.text }}
                      >
                        {dayjs(date).date()}
                      </AgText>
                    </Pressable>
                  </View>
                );
              })}
            </View>
          </View>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { width: '100%' },
  label: { marginBottom: 8 },
  trigger: {
    width: '100%',
    minHeight: 58,
    paddingHorizontal: 16,
    borderRadius: 14,
    borderWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  triggerContent: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  leftAccessory: { marginRight: 12 },
  triggerText: { flexShrink: 1 },
  error: { marginTop: 6 },
  modal: { flex: 1 },
  modalHeader: {
    minHeight: 68,
    paddingHorizontal: 20,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  closeButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  calendarBody: { paddingHorizontal: 20 },
  monthRow: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  monthButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  weekdayRow: { marginTop: 12, flexDirection: 'row' },
  weekdayCell: { flex: 1, alignItems: 'center' },
  grid: { marginTop: 4, flexDirection: 'row', flexWrap: 'wrap' },
  dayCell: { height: 48, alignItems: 'center', justifyContent: 'center' },
  dayButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
