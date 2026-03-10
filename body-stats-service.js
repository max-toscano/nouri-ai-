/**
 * body-stats-service.js
 *
 * All API calls for body stats go through this module.
 * Keeps network logic separate from UI code.
 *
 * Usage:
 *   const data = await BodyStatsService.get();   // null if none saved yet
 *   const saved = await BodyStatsService.save(payload);
 */

const BodyStatsService = (() => {
  const BASE = 'http://localhost:8000';

  /**
   * GET /api/body-stats/
   * Returns the most recent body stats row, or null if none exist yet.
   */
  async function get() {
    const res = await fetch(`${BASE}/api/body-stats/`);
    if (!res.ok) throw new Error(`GET /api/body-stats/ failed: ${res.status}`);
    return res.json(); // Django returns null (JSON null) when no row exists
  }

  /**
   * POST /api/body-stats/
   * Creates or updates (upsert) the single body stats row.
   * Returns the saved row.
   *
   * @param {Object} payload
   * @param {number|null} payload.weight
   * @param {string}      payload.weight_unit       - 'lbs' | 'kg'
   * @param {number|null} payload.height_feet
   * @param {number|null} payload.height_inches
   * @param {number|null} payload.height_cm
   * @param {string}      payload.height_unit        - 'ft' | 'cm'
   * @param {number|null} payload.age
   * @param {string|null} payload.sex                - 'M' | 'F'
   * @param {string|null} payload.activity_level     - 'sedentary'|'light'|'moderate'|'active'|'extra'
   * @param {number|null} payload.goal_weight
   * @param {number|null} payload.current_bmi
   * @param {number|null} payload.bmr
   * @param {number|null} payload.tdee
   */
  async function save(payload) {
    const res = await fetch(`${BASE}/api/body-stats/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(
        `POST /api/body-stats/ failed: ${res.status} – ${JSON.stringify(detail)}`
      );
    }

    return res.json();
  }

  return { get, save };
})();


/* ─── Calculation helpers ────────────────────────────────────────────────── */

/**
 * Convert raw user inputs to kg and cm.
 */
function bodyStatsToSI({ weight, weightUnit, heightFt, heightIn, heightCm, heightUnit }) {
  const wKg = weight == null ? null
    : weightUnit === 'lbs' ? weight * 0.453592
    : weight;

  const hCm = heightUnit === 'cm'
    ? (heightCm || null)
    : (((heightFt || 0) * 12 + (heightIn || 0)) * 2.54) || null;

  return { wKg, hCm };
}

/**
 * Calculate BMI, BMR (Mifflin-St Jeor), and TDEE.
 * Returns { bmi, bmr, tdee } — all null when inputs are incomplete.
 */
function calcBodyMetrics({ wKg, hCm, age, sex, activityLevel }) {
  if (!wKg || !hCm || !age) return { bmi: null, bmr: null, tdee: null };

  const hM  = hCm / 100;
  const bmi = Math.round((wKg / (hM * hM)) * 10) / 10;

  const bmrRaw = sex === 'M'
    ? (10 * wKg) + (6.25 * hCm) - (5 * age) + 5
    : (10 * wKg) + (6.25 * hCm) - (5 * age) - 161;
  const bmr = Math.round(bmrRaw);

  const MULTIPLIERS = {
    sedentary: 1.2,
    light:     1.375,
    moderate:  1.55,
    active:    1.725,
    extra:     1.9,
  };
  const tdee = Math.round(bmrRaw * (MULTIPLIERS[activityLevel] || 1.55));

  return { bmi, bmr, tdee };
}

/**
 * Human-readable BMI category.
 */
function bmiCategory(bmi) {
  if (bmi == null) return '';
  if (bmi < 18.5)  return 'Underweight';
  if (bmi < 25)    return 'Normal';
  if (bmi < 30)    return 'Overweight';
  return 'Obese';
}
