import React, { useMemo } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import {
  getWeekDays,
  shiftWeek,
  formatWeekRange,
  type DayInfo,
} from '../utils/dateHelpers';

interface WeeklyStripProps {
  /** The reference date used to calculate which week to display */
  referenceDate: Date;
  /** Currently selected date string (YYYY-MM-DD) */
  selectedDate: string;
  /** Called when user taps a day */
  onSelectDate: (dateString: string) => void;
  /** Called when user navigates to previous week */
  onPreviousWeek: () => void;
  /** Called when user navigates to next week */
  onNextWeek: () => void;
}

export default function WeeklyStrip({
  referenceDate,
  selectedDate,
  onSelectDate,
  onPreviousWeek,
  onNextWeek,
}: WeeklyStripProps) {
  const days = useMemo(() => getWeekDays(referenceDate), [referenceDate]);
  const weekLabel = useMemo(() => formatWeekRange(referenceDate), [referenceDate]);

  return (
    <View style={styles.container}>
      {/* Week navigation header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onPreviousWeek} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Text style={styles.arrow}>{'<'}</Text>
        </TouchableOpacity>
        <Text style={styles.weekLabel}>{weekLabel}</Text>
        <TouchableOpacity onPress={onNextWeek} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Text style={styles.arrow}>{'>'}</Text>
        </TouchableOpacity>
      </View>

      {/* Day pills */}
      <View style={styles.daysRow}>
        {days.map((day) => (
          <DayPill
            key={day.dateString}
            day={day}
            isSelected={day.dateString === selectedDate}
            onPress={() => onSelectDate(day.dateString)}
          />
        ))}
      </View>
    </View>
  );
}

// ── DayPill sub-component ────────────────────────────────────────────────────

interface DayPillProps {
  day: DayInfo;
  isSelected: boolean;
  onPress: () => void;
}

function DayPill({ day, isSelected, onPress }: DayPillProps) {
  return (
    <TouchableOpacity
      style={[
        styles.dayPill,
        isSelected && styles.dayPillSelected,
        day.isToday && !isSelected && styles.dayPillToday,
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Text
        style={[
          styles.dayLabel,
          isSelected && styles.dayLabelSelected,
        ]}
      >
        {day.label}
      </Text>
      <Text
        style={[
          styles.dayNumber,
          isSelected && styles.dayNumberSelected,
        ]}
      >
        {day.dayNumber}
      </Text>
      {day.isToday && <View style={[styles.todayDot, isSelected && styles.todayDotSelected]} />}
    </TouchableOpacity>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  arrow: {
    fontSize: 20,
    fontWeight: '600',
    color: '#667eea',
    paddingHorizontal: 8,
  },
  weekLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  daysRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  dayPill: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 44,
    height: 64,
    borderRadius: 12,
    backgroundColor: '#f5f5f5',
  },
  dayPillSelected: {
    backgroundColor: '#667eea',
  },
  dayPillToday: {
    backgroundColor: '#eef0ff',
    borderWidth: 1,
    borderColor: '#667eea',
  },
  dayLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#888',
    marginBottom: 4,
  },
  dayLabelSelected: {
    color: '#fff',
  },
  dayNumber: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  dayNumberSelected: {
    color: '#fff',
  },
  todayDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#667eea',
    marginTop: 3,
  },
  todayDotSelected: {
    backgroundColor: '#fff',
  },
});
