// ─── NOURISH API Service ──────────────────────────────────────────────────────
// All calls to the Django backend go through this module.
// Base URL matches the backend running locally.

const NourishAPI = (() => {
  const BASE = 'http://127.0.0.1:8000';

  /**
   * GET /api/meals/today/
   * Returns an array of today's logged meals.
   */
  async function loadTodayMeals() {
    const res = await fetch(`${BASE}/api/meals/today/`);
    if (!res.ok) throw new Error(`GET /api/meals/today/ failed: ${res.status}`);
    return res.json();
  }

  /**
   * GET /api/hydration/today/
   * Returns { total_ml, entries } for today.
   */
  async function loadTodayHydration() {
    const res = await fetch(`${BASE}/api/hydration/today/`);
    if (!res.ok) throw new Error(`GET /api/hydration/today/ failed: ${res.status}`);
    return res.json();
  }

  /**
   * POST /api/meals/
   * Saves a new meal entry and returns the saved object (with id).
   * @param {{ meal_type, food_name, calories, protein, carbs, fat, emoji, timestamp }} payload
   */
  async function saveMeal(payload) {
    const res = await fetch(`${BASE}/api/meals/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`POST /api/meals/ failed: ${res.status}`);
    return res.json();
  }

  /**
   * POST /api/hydration/
   * Saves a new hydration entry and returns the saved object (with id).
   * @param {{ amount_ml, timestamp }} payload
   */
  async function saveHydration(payload) {
    const res = await fetch(`${BASE}/api/hydration/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`POST /api/hydration/ failed: ${res.status}`);
    return res.json();
  }

  // ── Date-parameterized endpoints ──

  /**
   * GET /api/daily-summary/?date=YYYY-MM-DD
   * Returns aggregated daily totals for the given date.
   */
  async function loadDailySummary(date) {
    const res = await fetch(`${BASE}/api/daily-summary/?date=${date}`);
    if (!res.ok) throw new Error(`GET /api/daily-summary/ failed: ${res.status}`);
    return res.json();
  }

  /**
   * GET /api/meals/by-date/?date=YYYY-MM-DD
   * Returns all meal entries for the given date.
   */
  async function loadMealsByDate(date) {
    const res = await fetch(`${BASE}/api/meals/by-date/?date=${date}`);
    if (!res.ok) throw new Error(`GET /api/meals/by-date/ failed: ${res.status}`);
    return res.json();
  }

  /**
   * GET /api/hydration/by-date/?date=YYYY-MM-DD
   * Returns { date, total_ml, entries } for the given date.
   */
  async function loadHydrationByDate(date) {
    const res = await fetch(`${BASE}/api/hydration/by-date/?date=${date}`);
    if (!res.ok) throw new Error(`GET /api/hydration/by-date/ failed: ${res.status}`);
    return res.json();
  }

  /**
   * GET /api/week-summary/?start=YYYY-MM-DD
   * Returns { start, days: [...7 daily summaries] }.
   */
  async function loadWeekSummary(startDate) {
    const res = await fetch(`${BASE}/api/week-summary/?start=${startDate}`);
    if (!res.ok) throw new Error(`GET /api/week-summary/ failed: ${res.status}`);
    return res.json();
  }

  return {
    loadTodayMeals, loadTodayHydration, saveMeal, saveHydration,
    loadDailySummary, loadMealsByDate, loadHydrationByDate, loadWeekSummary,
  };
})();
