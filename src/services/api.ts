/**
 * Central API client for the Nourish Django backend.
 * All HTTP calls to the backend go through this module.
 */

// Use 10.0.2.2 for Android emulator, localhost for iOS simulator.
// For physical device, use your machine's LAN IP.
import { Platform } from 'react-native';

const BASE_URL = Platform.select({
  android: 'http://10.0.2.2:8000',
  ios: 'http://localhost:8000',
  default: 'http://127.0.0.1:8000',
});

// ── Types ────────────────────────────────────────────────────────────────────

export interface DailySummary {
  id: number;
  date: string;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  total_water_ml: number;
  meal_count: number;
  updated_at: string;
}

export interface MealEntry {
  id: number;
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  food_name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  emoji: string;
  timestamp: string;
  created_at: string;
}

export interface HydrationResponse {
  date: string;
  total_ml: number;
  entries: Array<{
    id: number;
    amount_ml: number;
    timestamp: string;
    created_at: string;
  }>;
}

export interface DailyGoals {
  id: number;
  calories_goal: number | null;
  protein_goal: number | null;
  carbs_goal: number | null;
  fat_goal: number | null;
  water_goal: number | null;
  goal_type: string | null;
  goal_rate: string | null;
  calculated_bmr: number | null;
  calculated_tdee: number | null;
  is_customized: boolean;
}

export interface WeekSummary {
  start: string;
  days: DailySummary[];
  weekly_calories: number;
  avg_daily: number;
  total_cal: number;
  goal_days: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return res.json();
}

async function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status}`);
  }
  return res.json();
}

// ── Public API ───────────────────────────────────────────────────────────────

/** Fetch aggregated daily totals for a specific date. */
export function getDailySummary(date: string): Promise<DailySummary> {
  return get(`/api/daily-summary/?date=${date}`);
}

/** Fetch all meal entries for a specific date. */
export function getMealsByDate(date: string): Promise<MealEntry[]> {
  return get(`/api/meals/by-date/?date=${date}`);
}

/** Fetch hydration total + entries for a specific date. */
export function getHydrationByDate(date: string): Promise<HydrationResponse> {
  return get(`/api/hydration/by-date/?date=${date}`);
}

/** Fetch daily summaries for an entire week (7 days from start). */
export function getWeekSummary(startDate: string): Promise<WeekSummary> {
  return get(`/api/week-summary/?start=${startDate}`);
}

/** Fetch the user's daily goals (singleton). */
export function getDailyGoals(): Promise<DailyGoals | null> {
  return get('/api/daily-goals/');
}

/** Save a new meal entry. */
export function createMeal(meal: Omit<MealEntry, 'id' | 'created_at'>): Promise<MealEntry> {
  return post('/api/meals/', meal as Record<string, unknown>);
}

/** Save a new hydration entry. */
export function createHydration(entry: { amount_ml: number; timestamp: string }): Promise<unknown> {
  return post('/api/hydration/', entry);
}
