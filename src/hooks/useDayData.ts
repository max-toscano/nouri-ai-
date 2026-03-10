import { useState, useEffect, useCallback } from 'react';
import {
  getDailySummary,
  getMealsByDate,
  getHydrationByDate,
  getDailyGoals,
  type DailySummary,
  type MealEntry,
  type HydrationResponse,
  type DailyGoals,
} from '../services/api';

export interface DayData {
  summary: DailySummary | null;
  meals: MealEntry[];
  hydration: HydrationResponse | null;
  goals: DailyGoals | null;
  loading: boolean;
  error: string | null;
}

/**
 * Fetches all day-level data (summary, meals, hydration, goals) for a given date.
 * Re-fetches automatically when `dateString` changes.
 */
export function useDayData(dateString: string): DayData & { refetch: () => void } {
  const [state, setState] = useState<DayData>({
    summary: null,
    meals: [],
    hydration: null,
    goals: null,
    loading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const [summary, meals, hydration, goals] = await Promise.all([
        getDailySummary(dateString),
        getMealsByDate(dateString),
        getHydrationByDate(dateString),
        getDailyGoals(),
      ]);
      setState({ summary, meals, hydration, goals, loading: false, error: null });
    } catch (err) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to load data',
      }));
    }
  }, [dateString]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refetch: fetchData };
}
