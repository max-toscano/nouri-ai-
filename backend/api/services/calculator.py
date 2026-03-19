"""
Nutrition calculator — Python port of macro-calculator.js.

Mifflin-St Jeor BMR, TDEE, calorie targets, and macro splits.
All tunable constants live here.
"""

# ── Activity multipliers ────────────────────────────────────────────────────

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light":     1.375,
    "moderate":  1.55,
    "active":    1.725,
    "extra":     1.9,
}

# ── Calorie adjustments per day ─────────────────────────────────────────────

# Deficit per day for each loss rate (lb/week)
DEFICIT_MAP = {
    "0.5": 250,
    "1.0": 500,
    "1.5": 750,
    "2.0": 1000,
}

# Surplus per day for each gain rate (lb/week)
# 1 lb ≈ 3,500 cal → X lb/week = X × 500 cal/day surplus
GAIN_SURPLUS_MAP = {
    "0.25": 125,
    "0.5":  250,
    "0.50": 250,
    "0.75": 375,
    "1.0":  500,
    "1.25": 625,
    "1.5":  750,
}

# ── Macro constants ─────────────────────────────────────────────────────────

PROTEIN_PER_LB = 0.9    # grams per lb bodyweight
FAT_PER_LB     = 0.35   # grams per lb bodyweight
CALS_PER_G_PROTEIN = 4
CALS_PER_G_CARB    = 4
CALS_PER_G_FAT     = 9

# ── Unit conversions ────────────────────────────────────────────────────────

LBS_TO_KG = 0.453592
INCHES_TO_CM = 2.54


def lbs_to_kg(lbs):
    return lbs * LBS_TO_KG


def feet_inches_to_cm(feet, inches=0):
    total_inches = (feet * 12) + (inches or 0)
    return total_inches * INCHES_TO_CM


# ── Core calculations ───────────────────────────────────────────────────────

def calc_bmr(weight_kg, height_cm, age, sex):
    """
    Mifflin-St Jeor BMR.

    Men:   BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age + 5
    Women: BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age - 161

    Returns rounded kcal/day or None if inputs incomplete.
    """
    if not weight_kg or not height_cm or not age:
        return None
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if sex == "M":
        return round(base + 5)
    return round(base - 161)


def calc_tdee(bmr, activity_level):
    """TDEE = BMR × activity multiplier."""
    if not bmr:
        return None
    mult = ACTIVITY_MULTIPLIERS.get(activity_level, ACTIVITY_MULTIPLIERS["moderate"])
    return round(bmr * mult)


def calc_bmi(weight_kg, height_cm):
    """BMI = weight(kg) / height(m)^2."""
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def calc_calorie_target(tdee, goal, rate=None):
    """
    Calorie target based on TDEE and goal.

    goal: "lose_weight" | "gain_weight" | "maingain"
    rate:
      - lose_weight: "0.5" | "1.0" | "1.5" | "2.0" (lb/week to lose)
      - gain_weight: "0.25" | "0.5" | "0.75" | "1.0" | "1.25" | "1.5" (lb/week to gain)
      - maingain: ignored (uses TDEE directly)
    """
    if not tdee:
        return None

    if goal == "lose_weight":
        deficit = DEFICIT_MAP.get(rate, DEFICIT_MAP["1.0"])
        return round(tdee - deficit)

    if goal == "gain_weight":
        surplus = GAIN_SURPLUS_MAP.get(rate, GAIN_SURPLUS_MAP["0.5"])
        return round(tdee + surplus)

    # maingain = maintenance
    return tdee


def calc_macros(calorie_target, weight_lbs):
    """
    Macro split from calorie target and bodyweight.

    Protein = 0.9g × bodyweight(lbs)
    Fat     = 0.35g × bodyweight(lbs)
    Carbs   = remaining calories ÷ 4
    """
    if not calorie_target or not weight_lbs:
        return None

    protein = round(weight_lbs * PROTEIN_PER_LB)
    fat = round(weight_lbs * FAT_PER_LB)
    used_cals = (protein * CALS_PER_G_PROTEIN) + (fat * CALS_PER_G_FAT)
    carb_cals = max(0, calorie_target - used_cals)
    carbs = round(carb_cals / CALS_PER_G_CARB)

    return {"protein": protein, "fat": fat, "carbs": carbs}


# ── High-level API ──────────────────────────────────────────────────────────

def get_weight_kg(body_stats):
    """Extract weight in kg from body stats dict (handles lbs/kg)."""
    weight = body_stats.get("weight")
    if not weight:
        return None
    if body_stats.get("weight_unit") == "kg":
        return weight
    return lbs_to_kg(weight)


def get_weight_lbs(body_stats):
    """Extract weight in lbs from body stats dict (handles lbs/kg)."""
    weight = body_stats.get("weight")
    if not weight:
        return None
    if body_stats.get("weight_unit") == "lbs" or not body_stats.get("weight_unit"):
        return weight
    return weight / LBS_TO_KG


def get_height_cm(body_stats):
    """Extract height in cm from body stats dict (handles ft/in and cm)."""
    if body_stats.get("height_unit") == "cm" and body_stats.get("height_cm"):
        return body_stats["height_cm"]
    feet = body_stats.get("height_feet")
    if feet:
        inches = body_stats.get("height_inches", 0)
        return feet_inches_to_cm(feet, inches)
    return body_stats.get("height_cm")


def recommend(body_stats, goal, rate_or_approach=None):
    """
    One-shot recommendation from body stats + goal.

    Args:
        body_stats: dict with weight, weight_unit, height_feet, height_inches,
                    height_cm, height_unit, age, sex, activity_level
        goal: "lose_weight" | "gain_weight" | "maingain"
        rate_or_approach: lb/week rate string (e.g. "1.0", "0.5")

    Returns:
        dict {bmr, tdee, bmi, calorie_target, protein, carbs, fat,
              deficit_or_surplus} or None if inputs incomplete
    """
    weight_kg = get_weight_kg(body_stats)
    weight_lbs = get_weight_lbs(body_stats)
    height_cm = get_height_cm(body_stats)
    age = body_stats.get("age")
    sex = body_stats.get("sex")
    activity_level = body_stats.get("activity_level")

    bmr = calc_bmr(weight_kg, height_cm, age, sex)
    tdee = calc_tdee(bmr, activity_level)
    bmi = calc_bmi(weight_kg, height_cm)
    calorie_target = calc_calorie_target(tdee, goal, rate_or_approach)
    macros = calc_macros(calorie_target, weight_lbs)

    if not bmr or not tdee or not calorie_target or not macros:
        return None

    return {
        "bmr": bmr,
        "tdee": tdee,
        "bmi": bmi,
        "calorie_target": calorie_target,
        "protein": macros["protein"],
        "carbs": macros["carbs"],
        "fat": macros["fat"],
        "deficit_or_surplus": calorie_target - tdee,
        "goal": goal,
    }
