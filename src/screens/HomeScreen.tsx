import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import WeeklyStrip from '../components/WeeklyStrip';
import { formatDateString, shiftWeek, getMonday } from '../utils/dateHelpers';
import { useDayData } from '../hooks/useDayData';
import { getWeekSummary } from '../services/api';
import type { MealEntry, WeekSummary } from '../services/api';

export default function HomeScreen() {
  // ── Week navigation state ──
  const [referenceDate, setReferenceDate] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(() => formatDateString(new Date()));

  // ── Data for the selected day ──
  const { summary, meals, hydration, goals, loading, error, refetch } = useDayData(selectedDate);

  // ── Weekly insights data ──
  const [weekData, setWeekData] = useState<WeekSummary | null>(null);

  useEffect(() => {
    const monday = getMonday(referenceDate);
    const startStr = formatDateString(monday);
    getWeekSummary(startStr)
      .then(setWeekData)
      .catch(() => setWeekData(null));
  }, [referenceDate]);

  // ── Week navigation handlers ──
  const goToPreviousWeek = useCallback(() => {
    setReferenceDate(prev => shiftWeek(prev, -1));
  }, []);

  const goToNextWeek = useCallback(() => {
    setReferenceDate(prev => shiftWeek(prev, 1));
  }, []);

  const handleSelectDate = useCallback((dateString: string) => {
    setSelectedDate(dateString);
  }, []);

  // ── Derived values ──
  const caloriesEaten = summary?.total_calories ?? 0;
  const caloriesGoal = goals?.calories_goal ?? 2000;
  const caloriesLeft = Math.max(0, caloriesGoal - caloriesEaten);
  const percentComplete = caloriesGoal > 0
    ? Math.min(100, Math.round((caloriesEaten / caloriesGoal) * 100))
    : 0;

  const proteinEaten = summary?.total_protein ?? 0;
  const carbsEaten = summary?.total_carbs ?? 0;
  const fatEaten = summary?.total_fat ?? 0;
  const proteinGoal = goals?.protein_goal ?? 150;
  const carbsGoal = goals?.carbs_goal ?? 250;
  const fatGoal = goals?.fat_goal ?? 65;

  const waterMl = hydration?.total_ml ?? 0;
  const waterGoal = goals?.water_goal ?? 2000;

  // ── Group meals by type ──
  const mealsByType = groupMealsByType(meals);

  return (
    <ScrollView
      style={styles.screen}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={refetch} />}
    >
      {/* ── Weekly Date Strip ── */}
      <WeeklyStrip
        referenceDate={referenceDate}
        selectedDate={selectedDate}
        onSelectDate={handleSelectDate}
        onPreviousWeek={goToPreviousWeek}
        onNextWeek={goToNextWeek}
      />

      {/* ── Weekly Insights ── */}
      {!loading && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Weekly Insights</Text>
          <View style={styles.weeklyRow}>
            <View style={styles.weeklyStat}>
              <Text style={styles.weeklyNumber}>
                {Math.round(weekData?.weekly_calories ?? 0)}
              </Text>
              <Text style={styles.weeklyLabel}>Weekly Cal</Text>
            </View>
            <View style={styles.weeklyStat}>
              <Text style={styles.weeklyNumber}>
                {Math.round(weekData?.avg_daily ?? 0)}
              </Text>
              <Text style={styles.weeklyLabel}>Avg Daily</Text>
            </View>
            <View style={styles.weeklyStat}>
              <Text style={styles.weeklyNumber}>
                {Math.round(weekData?.total_cal ?? 0)}
              </Text>
              <Text style={styles.weeklyLabel}>Total Cal</Text>
            </View>
            <View style={styles.weeklyStat}>
              <Text style={[styles.weeklyNumber, styles.goalDaysHighlight]}>
                {weekData?.goal_days ?? 0}
              </Text>
              <Text style={styles.weeklyLabel}>Goal Days</Text>
            </View>
          </View>
        </View>
      )}

      {/* ── Loading / Error ── */}
      {loading && !summary && (
        <View style={styles.centerBox}>
          <ActivityIndicator size="large" color="#667eea" />
        </View>
      )}
      {error && (
        <View style={styles.centerBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {/* ── Calorie Ring Summary ── */}
      {!loading && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Calories</Text>
          <View style={styles.calorieRow}>
            <View style={styles.calorieStat}>
              <Text style={styles.calorieNumber}>{Math.round(caloriesEaten)}</Text>
              <Text style={styles.calorieLabel}>Eaten</Text>
            </View>
            <View style={styles.calorieStat}>
              <Text style={[styles.calorieNumber, styles.calorieProgress]}>
                {percentComplete}%
              </Text>
              <Text style={styles.calorieLabel}>Complete</Text>
            </View>
            <View style={styles.calorieStat}>
              <Text style={styles.calorieNumber}>{Math.round(caloriesLeft)}</Text>
              <Text style={styles.calorieLabel}>Left</Text>
            </View>
          </View>
        </View>
      )}

      {/* ── Macros Bar ── */}
      {!loading && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Macros</Text>
          <View style={styles.macrosRow}>
            <MacroBar label="Protein" eaten={proteinEaten} goal={proteinGoal} color="#4CAF50" unit="g" />
            <MacroBar label="Carbs" eaten={carbsEaten} goal={carbsGoal} color="#FF9800" unit="g" />
            <MacroBar label="Fat" eaten={fatEaten} goal={fatGoal} color="#F44336" unit="g" />
          </View>
        </View>
      )}

      {/* ── Hydration ── */}
      {!loading && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Hydration</Text>
          {waterMl === 0 ? (
            <Text style={styles.emptyText}>No water logged yet.</Text>
          ) : (
            <View style={styles.hydrationRow}>
              <Text style={styles.hydrationAmount}>{Math.round(waterMl)} ml</Text>
              <Text style={styles.hydrationGoal}> / {Math.round(waterGoal)} ml</Text>
            </View>
          )}
          <View style={styles.progressBarBg}>
            <View
              style={[
                styles.progressBarFill,
                {
                  width: `${Math.min(100, (waterMl / waterGoal) * 100)}%`,
                  backgroundColor: '#2196F3',
                },
              ]}
            />
          </View>
        </View>
      )}

      {/* ── Today's Meals ── */}
      {!loading && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Meals</Text>
          {meals.length === 0 ? (
            <Text style={styles.emptyText}>No meals logged yet.</Text>
          ) : (
            Object.entries(mealsByType).map(([type, entries]) => (
              <View key={type} style={styles.mealGroup}>
                <Text style={styles.mealTypeLabel}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Text>
                {entries.map((meal) => (
                  <View key={meal.id} style={styles.mealRow}>
                    <Text style={styles.mealEmoji}>{meal.emoji}</Text>
                    <View style={styles.mealInfo}>
                      <Text style={styles.mealName}>{meal.food_name}</Text>
                      <Text style={styles.mealMacros}>
                        {Math.round(meal.calories)} kcal
                        {' \u00B7 '}P {Math.round(meal.protein)}g
                        {' \u00B7 '}C {Math.round(meal.carbs)}g
                        {' \u00B7 '}F {Math.round(meal.fat)}g
                      </Text>
                    </View>
                  </View>
                ))}
              </View>
            ))
          )}
        </View>
      )}

      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

// ── Helper: group meals ──────────────────────────────────────────────────────

function groupMealsByType(meals: MealEntry[]): Record<string, MealEntry[]> {
  const groups: Record<string, MealEntry[]> = {};
  const order = ['breakfast', 'lunch', 'dinner', 'snack'];
  for (const type of order) {
    const filtered = meals.filter(m => m.meal_type === type);
    if (filtered.length > 0) {
      groups[type] = filtered;
    }
  }
  return groups;
}

// ── MacroBar sub-component ───────────────────────────────────────────────────

function MacroBar({
  label,
  eaten,
  goal,
  color,
  unit,
}: {
  label: string;
  eaten: number;
  goal: number;
  color: string;
  unit: string;
}) {
  const pct = goal > 0 ? Math.min(100, (eaten / goal) * 100) : 0;
  return (
    <View style={styles.macroCol}>
      <Text style={styles.macroLabel}>{label}</Text>
      <View style={styles.progressBarBg}>
        <View style={[styles.progressBarFill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
      <Text style={styles.macroValue}>
        {Math.round(eaten)} / {Math.round(goal)} {unit}
      </Text>
    </View>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  centerBox: {
    padding: 32,
    alignItems: 'center',
  },
  errorText: {
    color: '#d32f2f',
    fontSize: 14,
  },
  card: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    fontStyle: 'italic',
  },

  // Weekly Insights
  weeklyRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  weeklyStat: {
    alignItems: 'center',
  },
  weeklyNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333',
  },
  weeklyLabel: {
    fontSize: 11,
    color: '#888',
    marginTop: 2,
  },
  goalDaysHighlight: {
    color: '#4CAF50',
  },

  // Calories
  calorieRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  calorieStat: {
    alignItems: 'center',
  },
  calorieNumber: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
  },
  calorieProgress: {
    color: '#667eea',
  },
  calorieLabel: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },

  // Macros
  macrosRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  macroCol: {
    flex: 1,
  },
  macroLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#555',
    marginBottom: 4,
  },
  macroValue: {
    fontSize: 11,
    color: '#888',
    marginTop: 4,
  },

  // Progress bars
  progressBarBg: {
    height: 6,
    backgroundColor: '#eee',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: 6,
    borderRadius: 3,
  },

  // Hydration
  hydrationRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  hydrationAmount: {
    fontSize: 20,
    fontWeight: '700',
    color: '#2196F3',
  },
  hydrationGoal: {
    fontSize: 14,
    color: '#888',
  },

  // Meals
  mealGroup: {
    marginBottom: 12,
  },
  mealTypeLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#667eea',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  mealRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
  },
  mealEmoji: {
    fontSize: 24,
    marginRight: 10,
  },
  mealInfo: {
    flex: 1,
  },
  mealName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  mealMacros: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
});
