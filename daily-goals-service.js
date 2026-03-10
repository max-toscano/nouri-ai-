/**
 * daily-goals-service.js
 *
 * All API calls for daily goals go through this module.
 * Mirrors the pattern used by body-stats-service.js and nourish-api.js.
 *
 * Usage:
 *   const goals = await DailyGoalsService.get();    // null if none saved yet
 *   const saved = await DailyGoalsService.save(payload);
 */

const DailyGoalsService = (() => {
  const BASE = 'http://127.0.0.1:8000';

  /**
   * GET /api/daily-goals/
   * Returns the most recent daily goals row, or null if none exist yet.
   */
  async function get() {
    const res = await fetch(`${BASE}/api/daily-goals/`);
    if (!res.ok) throw new Error(`GET /api/daily-goals/ failed: ${res.status}`);
    return res.json(); // Django returns JSON null when no row exists
  }

  /**
   * POST /api/daily-goals/
   * Creates or updates (upsert) the singleton daily goals row.
   * Returns the saved row.
   *
   * @param {Object} payload
   * @param {number|null} payload.calories_goal
   * @param {number|null} payload.protein_goal
   * @param {number|null} payload.carbs_goal
   * @param {number|null} payload.fat_goal
   * @param {number|null} payload.water_goal        - in ml (e.g. 2000 = 2 L)
   * @param {string|null} payload.goal_type         - 'lose' | 'maintain' | 'gain'
   * @param {string|null} payload.goal_rate         - '0.5' | '1.0' | '1.5' | '2.0'
   * @param {number|null} payload.calculated_bmr
   * @param {number|null} payload.calculated_tdee
   * @param {boolean}     payload.is_customized
   */
  async function save(payload) {
    const res = await fetch(`${BASE}/api/daily-goals/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(
        `POST /api/daily-goals/ failed: ${res.status} – ${JSON.stringify(detail)}`
      );
    }

    return res.json();
  }

  return { get, save };
})();
