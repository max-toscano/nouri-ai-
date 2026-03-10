/**
 * macro-calculator.js
 *
 * Pure helper functions for BMR, TDEE, calorie targets, and macro splits.
 * All tunable constants live here — adjust in one place to change app-wide behaviour.
 *
 * Usage:
 *   const rec = MacroCalculator.recommend({ wKg, hCm, age, sex, activityLevel,
 *                                           weightLbs, goalType, goalRate });
 *   // → { bmr, tdee, calories, protein, carbs, fat }
 */

const MacroCalculator = (() => {

  // ── Tunable constants ──────────────────────────────────────────────────────

  const ACTIVITY_MULTIPLIERS = {
    sedentary: 1.2,
    light:     1.375,
    moderate:  1.55,
    active:    1.725,
    extra:     1.9,
  };

  // Calorie deficit per day for each loss rate (lb/week)
  const DEFICIT_MAP = {
    '0.5': 250,
    '1.0': 500,
    '1.5': 750,
    '2.0': 1000,
  };

  // Calorie surplus per day for each gain rate (lb/week)
  const SURPLUS_MAP = {
    '0.5': 250,
    '1.0': 500,
  };

  // Macro ratios (per lb of bodyweight)
  const PROTEIN_PER_LB = 0.9;   // grams
  const FAT_PER_LB     = 0.35;  // grams

  // Calorie density
  const CALS_PER_G_PROTEIN = 4;
  const CALS_PER_G_CARB    = 4;
  const CALS_PER_G_FAT     = 9;

  // ── Core calculations ──────────────────────────────────────────────────────

  /**
   * Mifflin-St Jeor BMR.
   * @param {number} wKg   - weight in kg
   * @param {number} hCm   - height in cm
   * @param {number} age   - age in years
   * @param {string} sex   - 'M' | 'F'
   * @returns {number|null} BMR in kcal/day, or null if inputs are incomplete
   */
  function calcBMR(wKg, hCm, age, sex) {
    if (!wKg || !hCm || !age) return null;
    const base = (10 * wKg) + (6.25 * hCm) - (5 * age);
    return Math.round(sex === 'M' ? base + 5 : base - 161);
  }

  /**
   * TDEE = BMR × activity multiplier.
   * @param {number} bmr
   * @param {string} activityLevel - key from ACTIVITY_MULTIPLIERS
   * @returns {number|null}
   */
  function calcTDEE(bmr, activityLevel) {
    if (!bmr) return null;
    const mult = ACTIVITY_MULTIPLIERS[activityLevel] || ACTIVITY_MULTIPLIERS.moderate;
    return Math.round(bmr * mult);
  }

  /**
   * Calorie target based on TDEE and goal.
   * @param {number} tdee
   * @param {'lose'|'maintain'|'gain'} goalType
   * @param {string} goalRate - '0.5' | '1.0' | '1.5' | '2.0'
   * @returns {number|null}
   */
  function calcCalorieTarget(tdee, goalType, goalRate) {
    if (!tdee) return null;
    if (goalType === 'maintain') return tdee;
    if (goalType === 'lose')    return tdee - (DEFICIT_MAP[goalRate] || DEFICIT_MAP['1.0']);
    if (goalType === 'gain')    return tdee + (SURPLUS_MAP[goalRate] || SURPLUS_MAP['0.5']);
    return tdee;
  }

  /**
   * Macro split from calorie target and bodyweight in lbs.
   *
   * Strategy:
   *   1. Protein  = PROTEIN_PER_LB × weightLbs
   *   2. Fat      = FAT_PER_LB    × weightLbs
   *   3. Carbs    = remaining calories ÷ 4  (never negative)
   *
   * @param {number} calorieTarget
   * @param {number} weightLbs
   * @returns {{ protein: number, fat: number, carbs: number }|null}
   */
  function calcMacros(calorieTarget, weightLbs) {
    if (!calorieTarget || !weightLbs) return null;

    const protein    = Math.round(weightLbs * PROTEIN_PER_LB);
    const fat        = Math.round(weightLbs * FAT_PER_LB);
    const usedCals   = (protein * CALS_PER_G_PROTEIN) + (fat * CALS_PER_G_FAT);
    const carbCals   = Math.max(0, calorieTarget - usedCals);
    const carbs      = Math.round(carbCals / CALS_PER_G_CARB);

    return { protein, fat, carbs };
  }

  /**
   * One-shot recommendation from body stats + goal preferences.
   *
   * @param {Object} opts
   * @param {number}  opts.wKg          - weight in kg
   * @param {number}  opts.hCm          - height in cm
   * @param {number}  opts.age
   * @param {string}  opts.sex          - 'M' | 'F'
   * @param {string}  opts.activityLevel
   * @param {number}  opts.weightLbs    - weight in lbs (for macro calc)
   * @param {string}  opts.goalType     - 'lose' | 'maintain' | 'gain'
   * @param {string}  [opts.goalRate]   - '0.5' | '1.0' | '1.5' | '2.0'
   *
   * @returns {{ bmr, tdee, calories, protein, carbs, fat }|null}
   */
  function recommend({ wKg, hCm, age, sex, activityLevel, weightLbs, goalType, goalRate }) {
    const bmr           = calcBMR(wKg, hCm, age, sex);
    const tdee          = calcTDEE(bmr, activityLevel);
    const calories      = calcCalorieTarget(tdee, goalType, goalRate);
    const macros        = calcMacros(calories, weightLbs);

    if (!bmr || !tdee || !calories || !macros) return null;

    return {
      bmr,
      tdee,
      calories,
      protein: macros.protein,
      carbs:   macros.carbs,
      fat:     macros.fat,
    };
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  return { calcBMR, calcTDEE, calcCalorieTarget, calcMacros, recommend };

})();
