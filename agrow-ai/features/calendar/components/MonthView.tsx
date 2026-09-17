import dayjs from "dayjs";
import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { StyleSheet, TouchableOpacity, View } from "react-native";

import { AgCard, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import type { CalendarEvent } from "../types";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/** Month grid with activity markers; tap a day to focus its tasks. */
export function MonthView({
  events,
  selectedDate,
  onSelectDate,
}: {
  events: CalendarEvent[];
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const initial =
    selectedDate ?? events[0]?.scheduledDate ?? dayjs().format("YYYY-MM-DD");
  const [cursor, setCursor] = useState(() => dayjs(initial).startOf("month"));

  const eventDays = useMemo(() => {
    const map = new Map<string, boolean>();
    for (const e of events) {
      map.set(
        e.scheduledDate,
        map.get(e.scheduledDate) || e.status === "pending",
      );
    }
    return map;
  }, [events]);

  const today = dayjs().format("YYYY-MM-DD");
  const daysInMonth = cursor.daysInMonth();
  const leading = cursor.day();
  const cells: (string | null)[] = [
    ...Array.from({ length: leading }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) =>
      cursor.date(i + 1).format("YYYY-MM-DD"),
    ),
  ];

  return (
    <AgCard
      style={{
        backgroundColor: "#FFFFFF",
        borderColor: "#D7DDCF",
        borderRadius: 12,
      }}
    >
      <View className="flex-row items-center justify-between">
        <TouchableOpacity
          onPress={() => setCursor((c) => c.subtract(1, "month"))}
          accessibilityRole="button"
          accessibilityLabel={t("calendar.prevMonth")}
          activeOpacity={0.7}
          style={styles.navButton}
        >
          <ChevronLeft size={20} color="#153C24" />
        </TouchableOpacity>
        <AgText variant="body" weight="semibold" style={{ color: "#153C24" }}>
          {cursor.format("MMMM YYYY")}
        </AgText>
        <TouchableOpacity
          onPress={() => setCursor((c) => c.add(1, "month"))}
          accessibilityRole="button"
          accessibilityLabel={t("calendar.nextMonth")}
          activeOpacity={0.7}
          style={styles.navButton}
        >
          <ChevronRight size={20} color="#153C24" />
        </TouchableOpacity>
      </View>

      <View className="mt-3 flex-row">
        {WEEKDAYS.map((d) => (
          <View key={d} className="flex-1 items-center">
            <AgText variant="caption" style={{ color: "#667168" }}>
              {d}
            </AgText>
          </View>
        ))}
      </View>

      <View className="mt-1 flex-row flex-wrap">
        {cells.map((date, i) => {
          if (!date) {
            return (
              <View
                key={`b${i}`}
                style={{ width: `${100 / 7}%` }}
                className="h-11"
              />
            );
          }
          const hasEvents = eventDays.has(date);
          const pending = eventDays.get(date);
          const isSelected = date === selectedDate;
          const isToday = date === today;
          return (
            <View
              key={date}
              style={{ width: `${100 / 7}%` }}
              className="h-11 items-center"
            >
              <TouchableOpacity
                onPress={() => onSelectDate(date)}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                accessibilityLabel={dayjs(date).format("DD MMMM")}
                activeOpacity={0.7}
                style={[
                  styles.dayButton,
                  isSelected
                    ? styles.dayButtonSelected
                    : isToday
                      ? styles.dayButtonToday
                      : undefined,
                ]}
              >
                <AgText
                  variant="bodySmall"
                  weight={isToday || isSelected ? "bold" : "regular"}
                  style={{ color: isSelected ? "#FFFFFF" : "#26352B" }}
                >
                  {dayjs(date).date()}
                </AgText>
              </TouchableOpacity>
              {hasEvents ? (
                <View
                  className="h-1 w-1 rounded-full"
                  style={{
                    backgroundColor: pending ? colors.warning : colors.success,
                  }}
                />
              ) : (
                <View className="h-1 w-1" />
              )}
            </View>
          );
        })}
      </View>
    </AgCard>
  );
}

const styles = StyleSheet.create({
  navButton: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  dayButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  dayButtonSelected: { backgroundColor: "#176B36" },
  dayButtonToday: { backgroundColor: "#DDEDD7" },
});
