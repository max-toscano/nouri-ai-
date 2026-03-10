# ──────────────────────────────────────────────────────────────────────────────
# constants/quiz_choices.py  —  workout_quiz
#
# Single source of truth for every choice/enum used across the quiz.
# Serializers import from here — never hardcode allowed values in a serializer.
#
# Adding a future quiz section?
#   1. Add a new class below (TextChoices for strings, IntegerChoices for ints).
#   2. Import it in constants/__init__.py.
#   3. Use it in the matching serializer.
# ──────────────────────────────────────────────────────────────────────────────

from django.db import models


# ── Section 1: Goal ───────────────────────────────────────────────────────────

class GoalChoice(models.TextChoices):
    """
    The four fitness goals a user can select.

    Usage:
        GoalChoice.LOSE_WEIGHT          → "lose_weight"
        GoalChoice.LOSE_WEIGHT.label    → "Lose Weight"
        GoalChoice.choices              → [("gain_weight","Gain Weight"), ...]
    """
    GAIN_WEIGHT = "gain_weight", "Gain Weight"
    LOSE_WEIGHT = "lose_weight", "Lose Weight"
    MAINTAIN    = "maintain",    "Maintain"
    OTHER       = "other",       "Other"


# ── Section 2: Training Availability ─────────────────────────────────────────

class AvailableMinutes(models.IntegerChoices):
    """
    Allowed training session durations in minutes.

    Usage:
        AvailableMinutes.M60         → 60
        AvailableMinutes.M60.label   → "60 minutes"
        AvailableMinutes.choices     → [(30,"30 minutes"), (45,"45 minutes"), ...]
    """
    M30  = 30,  "30 minutes"
    M45  = 45,  "45 minutes"
    M60  = 60,  "60 minutes"
    M75  = 75,  "75 minutes"
    M90  = 90,  "90 minutes"
    M120 = 120, "120 minutes"


# ── Section 3: Training Experience ───────────────────────────────────────────

class ExperienceLevel(models.TextChoices):
    """
    How long / how seriously the user has trained.

    Usage:
        ExperienceLevel.BEGINNER        → "beginner"
        ExperienceLevel.BEGINNER.label  → "Beginner"
        ExperienceLevel.choices         → [("beginner","Beginner"), ...]
    """
    BEGINNER     = "beginner",     "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED     = "advanced",     "Advanced"


# ── Section 4: Equipment Access ───────────────────────────────────────────────

class EquipmentType(models.TextChoices):
    """
    High-level equipment categories the user can access or prefers to use.

    Used for both available_equipment_types and preferred_equipment_types.
    Both fields share the same allowed values — the subset validation
    (preferred ⊆ available) is enforced in EquipmentAccessSerializer.validate().

    Usage:
        EquipmentType.FREE_WEIGHTS        → "free_weights"
        EquipmentType.FREE_WEIGHTS.label  → "Free Weights"
        EquipmentType.values              → ["machines", "free_weights", "bodyweight"]
    """
    MACHINES     = "machines",     "Machines"
    FREE_WEIGHTS = "free_weights", "Free Weights"
    BODYWEIGHT   = "bodyweight",   "Bodyweight"


# ── Section 5: Body + Recovery Context ───────────────────────────────────────

class HeightUnitSystem(models.TextChoices):
    """
    Which unit system the user is using to input their height.
    The backend normalizes both to centimetres before storing/sending to the AI.
    """
    IMPERIAL = "imperial", "Imperial (ft / in)"
    METRIC   = "metric",   "Metric (cm)"


class SexChoice(models.TextChoices):
    """
    Biological sex, used by the AI to inform calorie/rep range estimates.
    prefer_not_to_say is always an option and must be handled gracefully.
    """
    MALE              = "male",              "Male"
    FEMALE            = "female",            "Female"
    OTHER             = "other",             "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer Not to Say"


class StressLevel(models.TextChoices):
    """
    Subjective daily stress level outside the gym.
    High stress = lower recovery capacity → the AI should reduce volume/intensity.
    """
    LOW      = "low",      "Low"
    MODERATE = "moderate", "Moderate"
    HIGH     = "high",     "High"


class ActivityLevelOutsideGym(models.TextChoices):
    """
    How active the user is in daily life outside of their gym sessions.
    Affects total daily energy expenditure and recovery needs.

    sedentary        → desk job, little movement
    lightly_active   → walks, light daily activity
    moderately_active → physical job or regular walks
    very_active      → labour-intensive job or high daily movement
    """
    SEDENTARY         = "sedentary",         "Sedentary"
    LIGHTLY_ACTIVE    = "lightly_active",    "Lightly Active"
    MODERATELY_ACTIVE = "moderately_active", "Moderately Active"
    VERY_ACTIVE       = "very_active",       "Very Active"


# ── Section 6: Injuries / Limitations ────────────────────────────────────────

class InjuredArea(models.TextChoices):
    """
    Body areas where the user reports pain or injury.

    The AI uses this list to avoid exercises that load the reported area.
    e.g. knees → no barbell squats, lunges, box jumps
         lower_back → no deadlifts, heavy rows, good mornings
         shoulders → no overhead press, upright rows
    """
    SHOULDERS  = "shoulders",  "Shoulders"
    ELBOWS     = "elbows",     "Elbows"
    WRISTS     = "wrists",     "Wrists"
    NECK       = "neck",       "Neck"
    UPPER_BACK = "upper_back", "Upper Back"
    LOWER_BACK = "lower_back", "Lower Back"
    HIPS       = "hips",       "Hips"
    KNEES      = "knees",      "Knees"
    ANKLES     = "ankles",     "Ankles"


class MovementToAvoid(models.TextChoices):
    """
    Movement patterns the user should avoid entirely.

    This gives the AI a direct constraint — independent of injured area —
    that the user has identified themselves as problematic.
    e.g. "squatting" blocks all squat variations regardless of knee entry
         "overhead_pressing" blocks all pressing above shoulder height
    """
    SQUATTING         = "squatting",         "Squatting"
    LUNGING           = "lunging",           "Lunging"
    BENDING           = "bending",           "Bending"
    OVERHEAD_PRESSING = "overhead_pressing", "Overhead Pressing"
    PUSHING           = "pushing",           "Pushing"
    PULLING           = "pulling",           "Pulling"
    JUMPING           = "jumping",           "Jumping"
    RUNNING           = "running",           "Running"


# ── Section 7: Exercise Preferences ──────────────────────────────────────────

class MuscleGroup(models.TextChoices):
    """
    Major muscle groups the user can flag for priority emphasis.

    When one or more groups are selected, the AI increases their weekly
    set volume and training frequency relative to non-prioritized muscles.

    Examples:
        ["shoulders", "glutes"] → extra sets on lateral raises, rear delts,
                                   hip thrusts, Bulgarian split squats
        ["back"]                → more rows and pull variations per week
        []                      → balanced volume across all muscle groups
    """
    CHEST      = "chest",      "Chest"
    BACK       = "back",       "Back"
    SHOULDERS  = "shoulders",  "Shoulders"
    BICEPS     = "biceps",     "Biceps"
    TRICEPS    = "triceps",    "Triceps"
    FOREARMS   = "forearms",   "Forearms"
    ABS        = "abs",        "Abs"
    GLUTES     = "glutes",     "Glutes"
    QUADS      = "quads",      "Quads"
    HAMSTRINGS = "hamstrings", "Hamstrings"
    CALVES     = "calves",     "Calves"


class TrainingStylePreference(models.TextChoices):
    """
    The user's preferred overall training style.

    The AI uses this to set the programming structure:
        bodybuilding    → hypertrophy rep ranges (8–12), isolation work, volume focus
        powerlifting    → strength rep ranges (1–5), compound-heavy, progressive overload
        general_fitness → balanced mix of strength + cardio + mobility
        no_preference   → let the AI decide based on the other quiz signals
    """
    BODYBUILDING    = "bodybuilding",    "Bodybuilding"
    POWERLIFTING    = "powerlifting",    "Powerlifting"
    GENERAL_FITNESS = "general_fitness", "General Fitness"
    NO_PREFERENCE   = "no_preference",   "No Preference"


class CardioType(models.TextChoices):
    """
    Types of cardio the user enjoys.

    Stored as a multi-select list.
    The AI uses this to choose which cardio modalities to include
    when the user opts in to cardio (wants_cardio = true).

    no_preference → include any cardio the AI deems appropriate
    """
    RUNNING       = "running",       "Running"
    CYCLING       = "cycling",       "Cycling"
    ROWING        = "rowing",        "Rowing"
    WALKING       = "walking",       "Walking"
    STAIR_CLIMBER = "stair_climber", "Stair Climber"
    HIIT          = "hiit",          "HIIT"
    SPORTS        = "sports",        "Sports"
    NO_PREFERENCE = "no_preference", "No Preference"


# ── Section 8: Adherence / Motivation ────────────────────────────────────────

class MotivationLevel(models.TextChoices):
    """
    How motivated the user is to train consistently.

    The AI uses this to calibrate program complexity and progression speed:
        low      → simple routines, short sessions, easy wins to build habit
        moderate → balanced programming with clear progression
        high     → challenging programs, faster overload, higher volume
    """
    LOW      = "low",      "Low"
    MODERATE = "moderate", "Moderate"
    HIGH     = "high",     "High"


class BiggestObstacle(models.TextChoices):
    """
    The user's primary barrier to working out consistently.

    The AI uses this to adjust program design to reduce friction:
        time        → shorter sessions, supersets, efficient formats
        motivation  → variety, engaging exercises, milestone goals
        energy      → lower intensity, better warm-up/cool-down structure
        injuries    → conservative loading, injury-safe alternatives
        knowledge   → simpler exercises, clearer instructions
        consistency → flexible scheduling, lower minimum commitment
    """
    TIME        = "time",        "Time"
    MOTIVATION  = "motivation",  "Motivation"
    ENERGY      = "energy",      "Energy"
    INJURIES    = "injuries",    "Injuries"
    KNOWLEDGE   = "knowledge",   "Knowledge"
    CONSISTENCY = "consistency", "Consistency"


class WorkoutIntensity(models.TextChoices):
    """
    The difficulty level the user prefers for their workouts.

        easy     → beginner-friendly, lower RPE, longer rest periods
        moderate → balanced challenge, standard rest, moderate RPE
        hard     → high-intensity, shorter rest, near-maximal effort
    """
    EASY     = "easy",     "Easy"
    MODERATE = "moderate", "Moderate"
    HARD     = "hard",     "Hard"


class AccountabilityPreference(models.TextChoices):
    """
    How the user prefers to stay accountable to their program.

        none                    → no accountability features needed
        reminders               → push notifications / session reminders
        progress_tracking       → visual logs, streaks, PRs, charts
        coaching_style_feedback → detailed feedback on performance, form cues
    """
    NONE                    = "none",                    "None"
    REMINDERS               = "reminders",               "Reminders"
    PROGRESS_TRACKING       = "progress_tracking",       "Progress Tracking"
    COACHING_STYLE_FEEDBACK = "coaching_style_feedback", "Coaching-Style Feedback"
