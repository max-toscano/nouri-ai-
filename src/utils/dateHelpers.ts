/**
 * Pure date utility functions for the weekly calendar strip.
 * No external dependencies — uses native Date API only.
 */

export interface DayInfo {
  /** Full Date object for this day */
  date: Date;
  /** Short weekday label: "MON", "TUE", etc. */
  label: string;
  /** Day-of-month number: 1–31 */
  dayNumber: number;
  /** ISO date string for API calls: "YYYY-MM-DD" */
  dateString: string;
  /** Whether this day is today */
  isToday: boolean;
}

const DAY_LABELS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'] as const;

/**
 * Format a Date as "YYYY-MM-DD" (local timezone, no UTC shift).
 */
export function formatDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/**
 * Get the Monday of the week containing `date`.
 * Week starts on Monday (ISO standard).
 */
export function getMonday(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat
  const diff = day === 0 ? -6 : 1 - day; // If Sunday, go back 6; otherwise go to Monday
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

/**
 * Generate the 7 days (Mon–Sun) for the week containing `referenceDate`.
 */
export function getWeekDays(referenceDate: Date): DayInfo[] {
  const monday = getMonday(referenceDate);
  const today = new Date();
  const todayStr = formatDateString(today);

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const dateString = formatDateString(d);
    return {
      date: d,
      label: DAY_LABELS[d.getDay()],
      dayNumber: d.getDate(),
      dateString,
      isToday: dateString === todayStr,
    };
  });
}

/**
 * Shift a reference date by N weeks.
 * Positive = forward, negative = backward.
 */
export function shiftWeek(referenceDate: Date, weeks: number): Date {
  const d = new Date(referenceDate);
  d.setDate(d.getDate() + weeks * 7);
  return d;
}

/**
 * Format a date range for display: "Mar 3 – 9, 2025"
 */
export function formatWeekRange(referenceDate: Date): string {
  const days = getWeekDays(referenceDate);
  const first = days[0].date;
  const last = days[6].date;

  const monthNames = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];

  if (first.getMonth() === last.getMonth()) {
    return `${monthNames[first.getMonth()]} ${first.getDate()} – ${last.getDate()}, ${first.getFullYear()}`;
  }
  return `${monthNames[first.getMonth()]} ${first.getDate()} – ${monthNames[last.getMonth()]} ${last.getDate()}, ${last.getFullYear()}`;
}

/**
 * Check if a date string represents today.
 */
export function isToday(dateString: string): boolean {
  return dateString === formatDateString(new Date());
}
