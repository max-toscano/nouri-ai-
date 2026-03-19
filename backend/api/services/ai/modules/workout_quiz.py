"""
Workout Quiz Module — Branching quiz with goal-specific AI prompts.

Quiz flow:
  1. Gateway question: lose_weight / gain_weight / maingain
  2. Shared core questions (fitness level, days, session, equipment, injuries, prefs)
  3. Path-specific extras (vary by goal)

Each goal gets its own system prompt so the AI tailors the program differently.
"""
from ..engine import AIEngine


# ─── Gateway question ────────────────────────────────────────────────────────

GOAL_QUESTION = {
    "id": "goal",
    "question": "What is your fitness goal?",
    "type": "single_choice",
    "options": [
        {
            "value": "lose_weight",
            "label": "Lose Weight",
            "description": "Burn fat while preserving muscle mass",
        },
        {
            "value": "gain_weight",
            "label": "Gain Weight",
            "description": "Build muscle and size with a calorie surplus",
        },
        {
            "value": "maingain",
            "label": "Maingain",
            "description": "Build muscle at maintenance calories — slow, steady recomposition",
        },
    ],
}

VALID_GOALS = {opt["value"] for opt in GOAL_QUESTION["options"]}


# ─── Shared core questions ───────────────────────────────────────────────────

CORE_QUESTIONS = [
    {
        "id": "fitness_level",
        "question": "What is your current fitness level?",
        "type": "single_choice",
        "options": [
            {"value": "beginner",     "label": "Beginner",     "description": "New to working out or returning after a long break"},
            {"value": "intermediate", "label": "Intermediate", "description": "Been training consistently for 6+ months"},
            {"value": "advanced",     "label": "Advanced",     "description": "2+ years of consistent, structured training"},
        ],
    },
    {
        "id": "days_per_week",
        "question": "How many days per week can you work out?",
        "type": "single_choice",
        "options": [
            {"value": 2, "label": "2 days"},
            {"value": 3, "label": "3 days"},
            {"value": 4, "label": "4 days"},
            {"value": 5, "label": "5 days"},
            {"value": 6, "label": "6 days"},
        ],
    },
    {
        "id": "session_length",
        "question": "How long can each workout session be?",
        "type": "single_choice",
        "options": [
            {"value": 30,  "label": "30 minutes"},
            {"value": 45,  "label": "45 minutes"},
            {"value": 60,  "label": "60 minutes"},
            {"value": 90,  "label": "90 minutes"},
            {"value": 120, "label": "120 minutes"},
        ],
    },
    {
        "id": "equipment",
        "question": "What equipment do you have access to?",
        "type": "multi_choice",
        "options": [
            {"value": "bodyweight",  "label": "Bodyweight only"},
            {"value": "dumbbells",   "label": "Dumbbells"},
            {"value": "barbell",     "label": "Barbell & plates"},
            {"value": "cables",      "label": "Cable machine"},
            {"value": "machines",    "label": "Gym machines"},
            {"value": "pull_up_bar", "label": "Pull-up bar"},
            {"value": "bands",       "label": "Resistance bands"},
            {"value": "kettlebell",  "label": "Kettlebells"},
            {"value": "full_gym",    "label": "Full commercial gym"},
        ],
    },
    {
        "id": "injuries",
        "question": "Do you have any injuries or physical limitations?",
        "type": "text",
        "placeholder": "e.g. 'Bad left knee', 'Lower back pain', or 'None'",
    },
    {
        "id": "preferences",
        "question": "Any exercise preferences or things you want to avoid?",
        "type": "text",
        "placeholder": "e.g. 'I love deadlifts', 'No running', or leave blank",
    },
]


# ─── Path-specific extra questions ───────────────────────────────────────────

PATH_QUESTIONS = {
    "lose_weight": [
        {
            "id": "loss_rate",
            "question": "How fast do you want to lose weight?",
            "type": "single_choice",
            "options": [
                {"value": "0.5", "label": "0.5 lb/week", "description": "Slow and steady — easier to maintain muscle"},
                {"value": "1.0", "label": "1.0 lb/week", "description": "Moderate pace — good balance of speed and sustainability"},
                {"value": "1.5", "label": "1.5 lb/week", "description": "Aggressive — requires strict discipline"},
                {"value": "2.0", "label": "2.0 lb/week", "description": "Maximum — only recommended for higher body fat"},
            ],
        },
        {
            "id": "cardio_preference",
            "question": "What is your cardio preference?",
            "type": "single_choice",
            "options": [
                {"value": "none",     "label": "No cardio",       "description": "Prefer to rely on diet alone for the deficit"},
                {"value": "light",    "label": "Light cardio",    "description": "Walking, easy cycling — 2-3x per week"},
                {"value": "moderate", "label": "Moderate cardio", "description": "Jogging, swimming, HIIT — 3-4x per week"},
                {"value": "heavy",    "label": "Heavy cardio",    "description": "Daily cardio sessions, endurance training"},
            ],
        },
    ],

    "gain_weight": [
        {
            "id": "bulk_approach",
            "question": "What kind of bulk are you going for?",
            "type": "single_choice",
            "options": [
                {"value": "lean",       "label": "Lean Bulk",       "description": "Slow and controlled — minimize fat gain"},
                {"value": "moderate",   "label": "Moderate Bulk",   "description": "Balanced pace — steady muscle gain with manageable fat"},
                {"value": "aggressive", "label": "Aggressive Bulk", "description": "Fast gains — maximize muscle growth, accept more fat"},
            ],
        },
        {
            "id": "gain_rate",
            "question": "How much weight do you want to gain per week?",
            "type": "single_choice",
            "depends_on": "bulk_approach",
            "options": [
                {"value": "0.25", "label": "0.25 lb/week", "description": "Very slow — minimal fat gain (+125 cal/day)",    "show_when": ["lean"]},
                {"value": "0.5",  "label": "0.5 lb/week",  "description": "Steady lean gains (+250 cal/day)",               "show_when": ["lean"]},
                {"value": "0.75", "label": "0.75 lb/week", "description": "Upper end of lean / lower moderate (+375 cal/day)", "show_when": ["lean", "moderate"]},
                {"value": "1.0",  "label": "1.0 lb/week",  "description": "Solid moderate pace (+500 cal/day)",             "show_when": ["moderate", "aggressive"]},
                {"value": "1.25", "label": "1.25 lb/week", "description": "Fast gains (+625 cal/day)",                      "show_when": ["aggressive"]},
                {"value": "1.5",  "label": "1.5 lb/week",  "description": "Maximum pace — aggressive surplus (+750 cal/day)", "show_when": ["aggressive"]},
            ],
        },
        {
            "id": "priority_muscles",
            "question": "What muscle areas do you want to prioritize?",
            "type": "single_choice",
            "options": [
                {"value": "upper_body",       "label": "Upper Body",       "description": "Chest, back, shoulders, arms"},
                {"value": "lower_body",       "label": "Lower Body",       "description": "Quads, hamstrings, glutes, calves"},
                {"value": "full_body",        "label": "Full Body",        "description": "Balanced — no specific priority"},
                {"value": "arms_shoulders",   "label": "Arms & Shoulders", "description": "Biceps, triceps, delts — aesthetic focus"},
                {"value": "back_chest",       "label": "Back & Chest",     "description": "Lats, traps, pecs — width and thickness"},
            ],
        },
    ],

    "maingain": [
        {
            "id": "priority_muscles",
            "question": "What muscle areas do you want to prioritize?",
            "type": "single_choice",
            "options": [
                {"value": "upper_body",       "label": "Upper Body",       "description": "Chest, back, shoulders, arms"},
                {"value": "lower_body",       "label": "Lower Body",       "description": "Quads, hamstrings, glutes, calves"},
                {"value": "full_body",        "label": "Full Body",        "description": "Balanced — no specific priority"},
                {"value": "arms_shoulders",   "label": "Arms & Shoulders", "description": "Biceps, triceps, delts — aesthetic focus"},
                {"value": "back_chest",       "label": "Back & Chest",     "description": "Lats, traps, pecs — width and thickness"},
            ],
        },
    ],
}


# ─── Shared JSON response format ────────────────────────────────────────────

_JSON_FORMAT = """\
RESPONSE FORMAT — return valid JSON exactly like this:
{
  "program_name": "string",
  "goal": "lose_weight | gain_weight | maingain",
  "summary": "1-2 sentence overview of the program",
  "weeks": 1,
  "days_per_week": number,
  "estimated_session_length": "string (e.g. '45-60 min')",
  "schedule": [
    {
      "day": "Day 1",
      "day_name": "Monday",
      "name": "Session Name",
      "is_rest_day": false,
      "warmup": ["exercise 1", "exercise 2"],
      "exercises": [
        {
          "name": "Exercise Name",
          "muscle_group": "chest",
          "sets": 3,
          "reps": "8-12",
          "rest_seconds": 90,
          "notes": "Form cue or tip"
        }
      ],
      "cooldown": ["stretch 1", "stretch 2"]
    },
    {
      "day": "Day 2",
      "day_name": "Tuesday",
      "name": "Rest Day",
      "is_rest_day": true,
      "warmup": [],
      "exercises": [],
      "cooldown": [],
      "rest_day_notes": "Light walking or stretching recommended"
    }
  ],
  "nutrition_notes": "Brief guidance on how to eat for this goal",
  "progression_notes": "When and how to increase difficulty",
  "tips": ["tip 1", "tip 2"]
}

Return ONLY the JSON — no markdown fences, no extra text."""


# ─── Shared base rules ──────────────────────────────────────────────────────

_BASE_RULES = """\
GENERAL RULES (apply to ALL programs):
1. Always consider the user's fitness level, goals, available equipment,
   injuries/limitations, and time availability.
2. Structure the program as a weekly plan with the exact number of training
   days the user requested, plus rest days to fill a 7-day week.
3. For each workout day include: a session name, warm-up (3-5 min),
   main exercises with sets/reps/rest, and cool-down stretches.
4. If the user is a beginner, favor simpler movements and full-body routines.
5. If the user has injuries or limitations, provide safe alternatives.
6. Only prescribe exercises that match the user's available equipment.
7. Include form cues for compound lifts."""


# ─── Goal-specific system prompts ───────────────────────────────────────────

SYSTEM_PROMPTS = {
    "lose_weight": f"""\
You are an expert certified personal trainer specializing in fat loss programs.
Your job is to create a personalized weekly workout program designed to help
the user LOSE WEIGHT (burn fat while preserving muscle mass).

{_BASE_RULES}

LOSE WEIGHT SPECIFIC RULES:
1. Design the program around a calorie deficit — the user will be eating less
   than their TDEE. Training should preserve muscle, not destroy the user.
2. Incorporate cardio based on the user's cardio preference:
   - "none": Zero dedicated cardio — focus entirely on resistance training.
   - "light": Add 2-3 low-intensity sessions (walking, easy cycling) on rest days.
   - "moderate": Include 3-4 moderate cardio sessions (jogging, swimming, or
     HIIT finishers at the end of lifting sessions).
   - "heavy": Program daily cardio — mix of LISS and HIIT.
3. Favor compound movements to maximize calorie burn per exercise.
4. Use moderate-to-high rep ranges (10-15) with shorter rest periods (45-75 sec)
   to keep heart rate elevated.
5. Consider circuit-style or superset formats to increase training density.
6. Match intensity to the user's target loss rate:
   - 0.5 lb/week: Conservative training volume, prioritize recovery.
   - 1.0 lb/week: Moderate volume and intensity.
   - 1.5 lb/week: Higher volume, more cardio integration.
   - 2.0 lb/week: Maximum training density, frequent cardio.
7. Always include a note reminding the user that nutrition (calorie deficit)
   is the primary driver of fat loss — training supports it.
8. Use progressive overload — even in a deficit, aim to maintain or slowly
   increase strength to signal the body to keep muscle.

{_JSON_FORMAT}
""",

    "gain_weight": f"""\
You are an expert certified personal trainer specializing in muscle-building
and hypertrophy programs. Your job is to create a personalized weekly workout
program designed to help the user GAIN WEIGHT (build muscle with a surplus).

{_BASE_RULES}

GAIN WEIGHT SPECIFIC RULES:
1. Design the program for a calorie surplus — the user will be eating above
   their TDEE. The exact surplus is calculated from their target gain rate.
   Training should maximize muscle stimulus and growth.
2. Emphasize progressive overload — the user should be adding weight or reps
   over time. Give clear guidance on progression.
3. Prioritize compound lifts (squat, bench, deadlift, overhead press, rows)
   as the foundation of every training day.
4. Use hypertrophy rep ranges (6-12 reps) for compounds, (10-15) for isolation.
5. Program adequate volume: 15-25 sets per muscle group per week for
   intermediate/advanced, 10-15 for beginners.
6. Prioritize the user's chosen muscle areas — give those areas extra volume
   and frequency (hit them 2-3x per week).
7. Match training volume and intensity to the user's bulk approach and gain rate:
   - "lean" (0.25-0.75 lb/wk): Moderate volume, careful progression, focus on
     compounds, keep accessories minimal. Small surplus means recovery is limited.
   - "moderate" (0.75-1.0 lb/wk): Standard hypertrophy volume, balanced compounds
     + isolation work. Good recovery capacity.
   - "aggressive" (1.0-1.5 lb/wk): High volume, extra accessory work, push
     intensity. Large surplus fuels maximum recovery and growth.
8. Include recovery guidance — with a surplus, the user can handle more volume
   but still needs adequate rest between sessions for the same muscle group.
   Larger surpluses allow more training volume.
9. Minimize cardio — only include light cardio for cardiovascular health
   (1-2 walks per week), never enough to eat into the surplus.

{_JSON_FORMAT}
""",

    "maingain": f"""\
You are an expert certified personal trainer specializing in body recomposition.
Your job is to create a personalized weekly workout program designed to help
the user MAINGAIN (build muscle at maintenance calories — slow, steady recomp).

{_BASE_RULES}

MAINGAIN SPECIFIC RULES:
1. Design the program for maintenance calories — the user is NOT in a surplus
   or deficit. Training must be efficient to drive muscle growth without
   relying on excess calories.
2. Emphasize progressive overload above all — since the user won't have extra
   calories to fuel recovery, the training stimulus must be precise and
   progressive. Every session should aim to beat the previous one.
3. Prioritize compound lifts as the foundation. Use moderate volume —
   enough to stimulate growth but not so much that recovery suffers at
   maintenance calories.
4. Program 12-18 sets per muscle group per week. Quality over quantity.
5. Prioritize the user's chosen muscle areas — give those areas extra
   frequency (hit them 2-3x per week) with slightly more volume.
6. Use a mix of rep ranges: heavy compounds (4-8 reps) for strength stimulus,
   moderate isolation (8-15 reps) for hypertrophy.
7. Include adequate rest days — recovery at maintenance is slower than in
   a surplus. Don't program back-to-back sessions for the same muscles.
8. Keep cardio minimal — 1-2 light sessions per week (walking) for health,
   nothing that significantly increases calorie expenditure.
9. Emphasize consistency and patience — maingaining is a long-term strategy.
   Results are slower but sustainable. Include a note about this.
10. Nutrition note: remind the user to keep protein high (0.8-1g per lb
    bodyweight) even at maintenance calories to support muscle protein synthesis.

{_JSON_FORMAT}
""",
}


# ─── Prompt builder ──────────────────────────────────────────────────────────

def build_prompt(quiz_answers, body_stats=None, nutrition=None):
    """
    Turn quiz answers + optional body stats + calculated nutrition
    into the user message sent to OpenAI.
    """
    parts = ["Here is my profile:\n"]

    # Body stats (from BodyStats model if available)
    if body_stats:
        if body_stats.get("weight"):
            unit = body_stats.get("weight_unit", "lbs")
            parts.append(f"- Weight: {body_stats['weight']} {unit}")
        if body_stats.get("height_feet"):
            parts.append(
                f"- Height: {body_stats['height_feet']}'"
                f"{body_stats.get('height_inches', 0)}\""
            )
        elif body_stats.get("height_cm"):
            parts.append(f"- Height: {body_stats['height_cm']} cm")
        if body_stats.get("age"):
            parts.append(f"- Age: {body_stats['age']}")
        if body_stats.get("sex"):
            parts.append(f"- Sex: {'Male' if body_stats['sex'] == 'M' else 'Female'}")
        if body_stats.get("activity_level"):
            parts.append(f"- Current activity level: {body_stats['activity_level']}")
        if body_stats.get("goal_weight"):
            parts.append(f"- Goal weight: {body_stats['goal_weight']} {body_stats.get('weight_unit', 'lbs')}")
        parts.append("")

    # Calculated nutrition (from calculator.py)
    if nutrition:
        parts.append("Calculated nutrition targets:")
        parts.append(f"- BMR: {nutrition['bmr']} kcal/day")
        parts.append(f"- TDEE: {nutrition['tdee']} kcal/day")
        if nutrition.get("bmi"):
            parts.append(f"- BMI: {nutrition['bmi']}")
        parts.append(f"- Daily calorie target: {nutrition['calorie_target']} kcal")
        diff = nutrition["deficit_or_surplus"]
        if diff < 0:
            parts.append(f"- Deficit: {abs(diff)} kcal/day below TDEE")
        elif diff > 0:
            parts.append(f"- Surplus: {diff} kcal/day above TDEE")
        else:
            parts.append(f"- Maintenance: eating at TDEE")
        parts.append(f"- Protein target: {nutrition['protein']}g/day")
        parts.append(f"- Carbs target: {nutrition['carbs']}g/day")
        parts.append(f"- Fat target: {nutrition['fat']}g/day")
        parts.append("")

    # Core quiz answers
    parts.append("Quiz answers:")

    goal = quiz_answers.get("goal", "")
    parts.append(f"- Goal: {goal}")

    core_labels = {
        "fitness_level": "Fitness level",
        "days_per_week": "Days available per week",
        "session_length": "Time per session (minutes)",
    }
    for key, label in core_labels.items():
        val = quiz_answers.get(key)
        if val is not None:
            parts.append(f"- {label}: {val}")

    equip = quiz_answers.get("equipment")
    if equip:
        if isinstance(equip, list):
            equip = ", ".join(equip)
        parts.append(f"- Available equipment: {equip}")

    if quiz_answers.get("injuries"):
        parts.append(f"- Injuries/limitations: {quiz_answers['injuries']}")
    if quiz_answers.get("preferences"):
        parts.append(f"- Preferences: {quiz_answers['preferences']}")

    # Path-specific answers
    if goal == "lose_weight":
        if quiz_answers.get("loss_rate"):
            parts.append(f"- Target loss rate: {quiz_answers['loss_rate']} lb/week")
        if quiz_answers.get("cardio_preference"):
            parts.append(f"- Cardio preference: {quiz_answers['cardio_preference']}")

    elif goal == "gain_weight":
        if quiz_answers.get("bulk_approach"):
            parts.append(f"- Bulk approach: {quiz_answers['bulk_approach']}")
        if quiz_answers.get("gain_rate"):
            parts.append(f"- Target gain rate: {quiz_answers['gain_rate']} lb/week")
        if quiz_answers.get("priority_muscles"):
            parts.append(f"- Priority muscle areas: {quiz_answers['priority_muscles']}")

    elif goal == "maingain":
        if quiz_answers.get("priority_muscles"):
            parts.append(f"- Priority muscle areas: {quiz_answers['priority_muscles']}")

    parts.append("\nPlease create my personalized workout program.")
    return "\n".join(parts)


# ─── Validation ──────────────────────────────────────────────────────────────

def _valid_values(question):
    """Extract the set of valid option values from a question definition."""
    return {opt["value"] for opt in question.get("options", [])}


def _find_question(question_list, question_id):
    """Find a question dict by id in a list of questions."""
    for q in question_list:
        if q["id"] == question_id:
            return q
    return None


def validate_quiz_answers(quiz_answers):
    """
    Validate all quiz answers against the question definitions.

    Returns (None) if valid, or a dict {"field": "error message"} for
    every invalid field. The frontend should not let the user proceed
    until all errors are resolved.
    """
    errors = {}

    # ── 1. Goal (required, must be valid) ────────────────────────────────
    goal = quiz_answers.get("goal")
    if not goal:
        errors["goal"] = "Goal is required. Choose: lose_weight, gain_weight, or maingain."
        return errors  # can't validate anything else without a goal
    if goal not in VALID_GOALS:
        errors["goal"] = f"Invalid goal '{goal}'. Valid: {sorted(VALID_GOALS)}."
        return errors

    # ── 2. Core questions ────────────────────────────────────────────────
    for question in CORE_QUESTIONS:
        qid = question["id"]
        val = quiz_answers.get(qid)
        qtype = question["type"]

        if qtype == "text":
            # Text fields are optional — no validation needed
            continue

        if qtype == "single_choice":
            valid = _valid_values(question)
            if val is None:
                errors[qid] = f"{qid} is required."
            elif val not in valid:
                errors[qid] = f"Invalid {qid} '{val}'. Valid: {sorted(valid, key=str)}."

        elif qtype == "multi_choice":
            valid = _valid_values(question)
            if not val or (isinstance(val, list) and len(val) == 0):
                errors[qid] = f"{qid} is required. Select at least one option."
            elif isinstance(val, list):
                bad = [v for v in val if v not in valid]
                if bad:
                    errors[qid] = f"Invalid {qid} values: {bad}. Valid: {sorted(valid)}."
            else:
                # Single value instead of list — check if it's valid
                if val not in valid:
                    errors[qid] = f"Invalid {qid} '{val}'. Valid: {sorted(valid)}."

    # ── 3. Path-specific questions ───────────────────────────────────────
    path_questions = PATH_QUESTIONS.get(goal, [])

    for question in path_questions:
        qid = question["id"]
        val = quiz_answers.get(qid)
        qtype = question["type"]

        if qtype == "text":
            continue

        if qtype == "single_choice":
            valid = _valid_values(question)

            # For dependent questions (gain_rate depends on bulk_approach),
            # also check show_when if the parent answer is available.
            depends_on = question.get("depends_on")
            if depends_on:
                parent_val = quiz_answers.get(depends_on)
                if parent_val:
                    # Filter to only options valid for this parent selection
                    valid = {
                        opt["value"] for opt in question["options"]
                        if parent_val in opt.get("show_when", [parent_val])
                    }

            if val is None:
                errors[qid] = f"{qid} is required."
            elif val not in valid:
                if depends_on and parent_val:
                    errors[qid] = (
                        f"Invalid {qid} '{val}' for {depends_on}='{parent_val}'. "
                        f"Valid: {sorted(valid, key=str)}."
                    )
                else:
                    errors[qid] = f"Invalid {qid} '{val}'. Valid: {sorted(valid, key=str)}."

    return errors if errors else None


def validate_body_data(body_data):
    """
    Validate body_data fields needed for BMR/TDEE calculation.

    Returns None if valid, or a dict {"field": "error message"} for
    every invalid field.
    """
    errors = {}

    if not body_data or not isinstance(body_data, dict) or len(body_data) == 0:
        return {"body_data": "body_data is required for calorie calculations."}

    # Weight
    weight = body_data.get("weight")
    if weight is None:
        errors["weight"] = "Weight is required."
    elif not isinstance(weight, (int, float)) or weight <= 0:
        errors["weight"] = "Weight must be a positive number."

    weight_unit = body_data.get("weight_unit", "lbs")
    if weight_unit not in ("lbs", "kg"):
        errors["weight_unit"] = "weight_unit must be 'lbs' or 'kg'."

    # Height
    height_unit = body_data.get("height_unit", "ft")
    if height_unit not in ("ft", "cm"):
        errors["height_unit"] = "height_unit must be 'ft' or 'cm'."
    elif height_unit == "ft":
        feet = body_data.get("height_feet")
        if feet is None:
            errors["height_feet"] = "height_feet is required when height_unit is 'ft'."
        elif not isinstance(feet, (int, float)) or feet < 1 or feet > 8:
            errors["height_feet"] = "height_feet must be between 1 and 8."
        inches = body_data.get("height_inches", 0)
        if inches is not None and (not isinstance(inches, (int, float)) or inches < 0 or inches >= 12):
            errors["height_inches"] = "height_inches must be between 0 and 11."
    else:
        cm = body_data.get("height_cm")
        if cm is None:
            errors["height_cm"] = "height_cm is required when height_unit is 'cm'."
        elif not isinstance(cm, (int, float)) or cm < 50 or cm > 280:
            errors["height_cm"] = "height_cm must be between 50 and 280."

    # Age
    age = body_data.get("age")
    if age is None:
        errors["age"] = "Age is required."
    elif not isinstance(age, (int, float)) or age < 13 or age > 120:
        errors["age"] = "Age must be between 13 and 120."

    # Sex
    sex = body_data.get("sex")
    if not sex:
        errors["sex"] = "Sex is required. Valid: 'M' or 'F'."
    elif sex not in ("M", "F"):
        errors["sex"] = "Sex must be 'M' or 'F'."

    # Activity level
    activity = body_data.get("activity_level")
    valid_activity = {"sedentary", "light", "moderate", "active", "extra"}
    if not activity:
        errors["activity_level"] = f"activity_level is required. Valid: {sorted(valid_activity)}."
    elif activity not in valid_activity:
        errors["activity_level"] = f"Invalid activity_level '{activity}'. Valid: {sorted(valid_activity)}."

    return errors if errors else None


# ─── Public API ──────────────────────────────────────────────────────────────

def get_questions(goal=None):
    """
    Return quiz questions for the frontend.

    - No goal  → returns just the gateway question (step 1)
    - With goal → returns core + path-specific questions (step 2)
    """
    if goal is None:
        return {
            "step": "goal",
            "questions": [GOAL_QUESTION],
        }

    if goal not in VALID_GOALS:
        raise ValueError(
            f"Invalid goal '{goal}'. Valid: {sorted(VALID_GOALS)}"
        )

    return {
        "step": "details",
        "goal": goal,
        "questions": CORE_QUESTIONS + PATH_QUESTIONS[goal],
    }


def generate(quiz_answers, body_stats=None, nutrition=None):
    """
    Generate a workout program from quiz answers.

    Picks the correct system prompt based on the user's goal, builds
    the user message (including calculated nutrition), and sends to
    the AI engine.
    """
    goal = quiz_answers.get("goal")
    if not goal or goal not in VALID_GOALS:
        raise ValueError(
            f"quiz_answers must include a valid 'goal'. Valid: {sorted(VALID_GOALS)}"
        )

    system_prompt = SYSTEM_PROMPTS[goal]
    engine = AIEngine()
    user_message = build_prompt(quiz_answers, body_stats, nutrition)
    return engine.chat(system_prompt, user_message, expect_json=True)
