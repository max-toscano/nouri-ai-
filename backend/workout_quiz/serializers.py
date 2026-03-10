# ──────────────────────────────────────────────────────────────────────────────
# serializers.py  —  workout_quiz
#
# STRUCTURE
# ---------
# Each quiz section has its own serializer class.
# The top-level QuizSerializer composes them all via nested fields.
#
# Currently implemented sections:
#   1. Goal               → GoalSerializer
#   2. Training Avail.    → DayAvailabilitySerializer
#                           TrainingAvailabilitySerializer
#   3. Training Exp.      → TrainingExperienceSerializer
#   4. Equipment Access   → EquipmentAccessSerializer
#   5. Body + Recovery    → BodyRecoveryContextSerializer
#   6. Injuries           → InjuryLimitationsSerializer
#   7. Exercise Prefs     → SelectedExerciseSerializer
#                           ExercisePreferencesSerializer
#
# To add a new section later:
#   1. Create a new serializer class here.
#   2. Add a field for it in QuizSerializer.
#   3. Add its choices to constants/quiz_choices.py.
# ──────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from .constants import (
    GoalChoice,
    AvailableMinutes,
    ExperienceLevel,
    EquipmentType,
    HeightUnitSystem,
    SexChoice,
    StressLevel,
    ActivityLevelOutsideGym,
    InjuredArea,
    MovementToAvoid,
    MuscleGroup,
    TrainingStylePreference,
    CardioType,
    MotivationLevel,
    BiggestObstacle,
    WorkoutIntensity,
    AccountabilityPreference,
)


# ── Section 1: Goal ───────────────────────────────────────────────────────────

class GoalDetailsSerializer(serializers.Serializer):
    """
    Nested weight data collected inside the Goal section.

    Fields
    ------
    current_weight_kg  — always required (numeric, 25–400)
    target_weight_kg   — required for gain/lose, must be null for maintain,
                         optional/null for other

    NOTE: directional validation (target > current for gain, target < current
    for lose) is enforced one level up in GoalSerializer and QuizSerializer,
    because that check needs access to the `goal` field which lives outside
    this nested object.
    """

    current_weight_kg = serializers.FloatField(
        min_value=25,
        max_value=400,
        help_text="User's current weight in kg. Range: 25–400.",
    )

    target_weight_kg = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=25,
        max_value=400,
        help_text=(
            "User's target weight in kg. Required for gain_weight and lose_weight. "
            "Must be null for maintain."
        ),
    )


class GoalSerializer(serializers.Serializer):
    """
    Validates the Goal section as a standalone unit.
    Used by POST /api/quiz/goal/ for isolated testing.

    Fields
    ------
    goal            — one of GoalChoice (required)
    goal_other_text — free-text, required only when goal="other"
    goal_details    — nested weight data (GoalDetailsSerializer)

    Validation logic
    ----------------
    All cross-field rules live here because they span both the top-level
    `goal` field and the nested `goal_details` fields:

    | goal          | goal_other_text | target_weight_kg           |
    |---------------|-----------------|----------------------------|
    | gain_weight   | ignored         | required, must be > current |
    | lose_weight   | ignored         | required, must be < current |
    | maintain      | ignored         | must be null               |
    | other         | required        | optional / null            |
    """

    goal = serializers.ChoiceField(
        choices=GoalChoice.choices,
        help_text="One of: gain_weight | lose_weight | maintain | other",
    )

    goal_other_text = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text='Required when goal is "other". Leave null otherwise.',
    )

    goal_details = GoalDetailsSerializer(
        help_text="Current and target weight data.",
    )

    def validate(self, data):
        goal         = data.get("goal")
        details      = data.get("goal_details") or {}
        current      = details.get("current_weight_kg")
        target       = details.get("target_weight_kg")
        other_text   = data.get("goal_other_text") or ""

        # ── "other" requires explanation ──────────────────────────────────────
        if goal == GoalChoice.OTHER and not other_text.strip():
            raise serializers.ValidationError(
                {"goal_other_text": 'Required when goal is "other".'}
            )

        # ── gain / lose require a target weight ───────────────────────────────
        if goal in (GoalChoice.GAIN_WEIGHT, GoalChoice.LOSE_WEIGHT):
            if target is None:
                raise serializers.ValidationError(
                    {"goal_details": {"target_weight_kg": f'Required when goal is "{goal}".'}},
                )

        # ── maintain must NOT have a target weight ────────────────────────────
        if goal == GoalChoice.MAINTAIN and target is not None:
            raise serializers.ValidationError(
                {"goal_details": {"target_weight_kg": 'Must be null when goal is "maintain".'}},
            )

        # ── directional checks (only when both weights are present) ───────────
        if goal == GoalChoice.GAIN_WEIGHT and target is not None and current is not None:
            if target <= current:
                raise serializers.ValidationError(
                    {"goal_details": {"target_weight_kg": "Target weight must be greater than current weight when gaining weight."}}
                )

        if goal == GoalChoice.LOSE_WEIGHT and target is not None and current is not None:
            if target >= current:
                raise serializers.ValidationError(
                    {"goal_details": {"target_weight_kg": "Target weight must be less than current weight when losing weight."}}
                )

        return data


# ── Section 2: Training Availability ─────────────────────────────────────────

class DayAvailabilitySerializer(serializers.Serializer):
    """
    Validates a single day's training availability.

    Rules enforced here:
    - When is_available = false  → available_minutes, start_time, end_time must be null
    - When is_available = true   → start_time and end_time are required,
                                   start_time must be strictly before end_time
    """

    is_available = serializers.BooleanField(
        help_text="Whether the user can train on this day.",
    )

    available_minutes = serializers.ChoiceField(
        choices=AvailableMinutes.choices,  # 30 | 45 | 60 | 75 | 90 | 120
        required=False,
        allow_null=True,
        help_text="Planned session length in minutes. Null when not available.",
    )

    # TimeField parses strings like "06:00", "18:30", "23:59" into datetime.time.
    # format="%H:%M" ensures the response serializes back as "HH:MM" (not "HH:MM:SS").
    start_time = serializers.TimeField(
        required=False,
        allow_null=True,
        format="%H:%M",
        input_formats=["%H:%M", "%H:%M:%S"],
        help_text='24-hour start time, e.g. "06:00". Null when not available.',
    )

    end_time = serializers.TimeField(
        required=False,
        allow_null=True,
        format="%H:%M",
        input_formats=["%H:%M", "%H:%M:%S"],
        help_text='24-hour end time, e.g. "07:30". Must be after start_time.',
    )

    def validate(self, data):
        is_available     = data.get("is_available")
        available_minutes = data.get("available_minutes")
        start_time       = data.get("start_time")
        end_time         = data.get("end_time")

        if not is_available:
            # ── Day is OFF — everything else must be null ─────────────────────
            errors = {}
            if available_minutes is not None:
                errors["available_minutes"] = "Must be null when is_available is false."
            if start_time is not None:
                errors["start_time"] = "Must be null when is_available is false."
            if end_time is not None:
                errors["end_time"] = "Must be null when is_available is false."
            if errors:
                raise serializers.ValidationError(errors)

        else:
            # ── Day is ON — time window is required and must be logical ───────
            errors = {}
            if start_time is None:
                errors["start_time"] = "Required when is_available is true."
            if end_time is None:
                errors["end_time"] = "Required when is_available is true."

            if errors:
                raise serializers.ValidationError(errors)

            # Both times are present — ensure the window is valid
            if start_time >= end_time:
                raise serializers.ValidationError(
                    {"end_time": "end_time must be later than start_time."}
                )

        return data


class TrainingAvailabilitySerializer(serializers.Serializer):
    """
    Wraps all 7 days of the week.
    Each day is independently validated by DayAvailabilitySerializer.

    The full week is always required — send every day even if is_available=false.
    This makes the data structure predictable for the AI prompt builder.
    """

    monday    = DayAvailabilitySerializer()
    tuesday   = DayAvailabilitySerializer()
    wednesday = DayAvailabilitySerializer()
    thursday  = DayAvailabilitySerializer()
    friday    = DayAvailabilitySerializer()
    saturday  = DayAvailabilitySerializer()
    sunday    = DayAvailabilitySerializer()


# ── Section 3: Training Experience ───────────────────────────────────────────

class TrainingExperienceSerializer(serializers.Serializer):
    """
    Validates the Training Experience section.

    Fields
    ------
    training_experience_level       — beginner | intermediate | advanced
    months_training_consistently    — integer, 0–600
    familiar_with_gym_equipment     — boolean
    comfortable_with_compound_lifts — boolean

    Why these fields matter for the AI
    ------------------------------------
    - experience_level sets the overall program complexity ceiling.
    - months_training_consistently gives the AI a more precise signal than
      the level label alone (e.g. a 1-month "intermediate" vs a 24-month one).
    - comfortable_with_compound_lifts tells the AI whether to assign squats,
      deadlifts, bench press, overhead press, and barbell rows — or to
      substitute machine / bodyweight alternatives instead.
    """

    training_experience_level = serializers.ChoiceField(
        choices=ExperienceLevel.choices,
        help_text="One of: beginner | intermediate | advanced",
    )

    months_training_consistently = serializers.IntegerField(
        min_value=0,
        max_value=600,
        help_text="How many months the user has trained consistently. Range: 0–600.",
    )

    familiar_with_gym_equipment = serializers.BooleanField(
        help_text="Whether the user knows how to use standard gym machines and free weights.",
    )

    comfortable_with_compound_lifts = serializers.BooleanField(
        help_text=(
            "Whether the user is comfortable with compound barbell movements "
            "(squat, deadlift, bench press, overhead press, barbell row). "
            "The AI uses this to decide whether to include or avoid these exercises."
        ),
    )


# ── Section 4: Equipment Access ───────────────────────────────────────────────

class EquipmentAccessSerializer(serializers.Serializer):
    """
    Validates the Equipment Access section.

    Fields
    ------
    available_equipment_types  — what the user has access to (multi-select)
    preferred_equipment_types  — what the user wants to use (multi-select)

    Both fields share the same three allowed values: machines | free_weights | bodyweight.

    Key validation rules
    --------------------
    - Each list must contain at least one item.
    - Duplicates are silently removed (list → set → sorted list).
    - preferred_equipment_types must be a subset of available_equipment_types.
      e.g. you cannot prefer machines if you don't have access to machines.
    """

    # ListField wraps a ChoiceField child so each element in the list is
    # independently validated against the allowed values.
    # An invalid element like "dumbbells" is rejected with a clear error message.
    available_equipment_types = serializers.ListField(
        child=serializers.ChoiceField(choices=EquipmentType.choices),
        min_length=1,
        help_text="At least one of: machines | free_weights | bodyweight",
    )

    preferred_equipment_types = serializers.ListField(
        child=serializers.ChoiceField(choices=EquipmentType.choices),
        min_length=1,
        help_text=(
            "At least one of: machines | free_weights | bodyweight. "
            "Every value here must also appear in available_equipment_types."
        ),
    )

    def validate_available_equipment_types(self, value):
        # Remove duplicates and return a stable sorted list.
        # Sorting keeps the response consistent regardless of submission order.
        return sorted(set(value))

    def validate_preferred_equipment_types(self, value):
        # Same deduplication as above.
        return sorted(set(value))

    def validate(self, data):
        available = set(data.get("available_equipment_types", []))
        preferred = set(data.get("preferred_equipment_types", []))

        # preferred must be a subset of available —
        # you can't prefer equipment you don't have access to.
        invalid = preferred - available
        if invalid:
            raise serializers.ValidationError(
                {
                    "preferred_equipment_types": (
                        f"The following types are not in available_equipment_types: "
                        f"{sorted(invalid)}. "
                        f"You can only prefer equipment you have access to."
                    )
                }
            )

        return data


# ── Section 5: Body + Recovery Context ───────────────────────────────────────

class BodyRecoveryContextSerializer(serializers.Serializer):
    """
    Collects body metrics and recovery factors.

    Height input
    ------------
    The user picks a unit system first (imperial or metric), then provides
    the matching fields.  The backend normalises everything to
    `normalized_height_cm` inside validate() so the rest of the system
    only ever sees one consistent value.

    Imperial → (feet * 30.48) + (inches * 2.54)
    Metric   → height_cm as-is

    Fields that are irrelevant for the chosen unit system must be null.
    This keeps the contract explicit and prevents ambiguous submissions.

    Weight
    ------
    current_weight_kg is NOT collected here — it was already collected
    in the Goal section (goal_details.current_weight_kg).
    """

    # ── Demographic ───────────────────────────────────────────────────────────
    age = serializers.IntegerField(
        min_value=13,
        max_value=100,
        help_text="User's age in years. Range: 13–100.",
    )

    sex = serializers.ChoiceField(
        choices=SexChoice.choices,
        help_text="One of: male | female | other | prefer_not_to_say",
    )

    # ── Height: unit system selector ─────────────────────────────────────────
    height_unit_system = serializers.ChoiceField(
        choices=HeightUnitSystem.choices,
        help_text="Which unit system the user is using: imperial | metric",
    )

    # ── Height: imperial fields (null when metric) ────────────────────────────
    height_feet = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=3,
        max_value=8,
        help_text="Whole feet component. Required when height_unit_system is imperial. Range: 3–8.",
    )

    height_inches = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=11,
        help_text="Remaining inches component. Required when height_unit_system is imperial. Range: 0–11.",
    )

    # ── Height: metric field (null when imperial) ─────────────────────────────
    height_cm = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=100,
        max_value=250,
        help_text="Height in centimetres. Required when height_unit_system is metric. Range: 100–250.",
    )

    # ── Recovery factors ──────────────────────────────────────────────────────
    sleep_hours = serializers.FloatField(
        min_value=0,
        max_value=24,
        help_text="Average nightly sleep in hours. Range: 0–24.",
    )

    stress_level = serializers.ChoiceField(
        choices=StressLevel.choices,
        help_text="Subjective daily stress level: low | moderate | high",
    )

    activity_level_outside_gym = serializers.ChoiceField(
        choices=ActivityLevelOutsideGym.choices,
        help_text=(
            "How active the user is in daily life outside training: "
            "sedentary | lightly_active | moderately_active | very_active"
        ),
    )

    def validate(self, data):
        unit_system   = data.get("height_unit_system")
        height_feet   = data.get("height_feet")
        height_inches = data.get("height_inches")
        height_cm     = data.get("height_cm")

        if unit_system == HeightUnitSystem.IMPERIAL:
            # ── Imperial: feet + inches required; height_cm must be absent ────
            errors = {}
            if height_feet is None:
                errors["height_feet"] = "Required when height_unit_system is imperial."
            if height_inches is None:
                errors["height_inches"] = "Required when height_unit_system is imperial."
            if height_cm is not None:
                errors["height_cm"] = "Must be null when height_unit_system is imperial."
            if errors:
                raise serializers.ValidationError(errors)

            # Compute the single normalised value the AI will use
            data["normalized_height_cm"] = round(
                (height_feet * 30.48) + (height_inches * 2.54), 2
            )

        elif unit_system == HeightUnitSystem.METRIC:
            # ── Metric: height_cm required; imperial fields must be absent ─────
            errors = {}
            if height_cm is None:
                errors["height_cm"] = "Required when height_unit_system is metric."
            if height_feet is not None:
                errors["height_feet"] = "Must be null when height_unit_system is metric."
            if height_inches is not None:
                errors["height_inches"] = "Must be null when height_unit_system is metric."
            if errors:
                raise serializers.ValidationError(errors)

            data["normalized_height_cm"] = round(float(height_cm), 2)

        return data


# ── Section 6: Injuries / Limitations ────────────────────────────────────────

class InjuryLimitationsSerializer(serializers.Serializer):
    """
    Collects injury and movement limitation data.

    This section acts as a safety layer for the workout generator.
    The AI must cross-reference these values against every exercise it
    considers before including it in the program:

        injured_areas    → block exercises that directly load that joint/area
        movements_to_avoid → block entire movement patterns regardless of area

    Both lists use the same multi-select + deduplication pattern as
    EquipmentAccessSerializer.

    Conditional rules
    -----------------
    has_injuries = false → injured_areas, movements_to_avoid, injury_notes
                           must all be empty / null (nothing to report)
    has_injuries = true  → injured_areas must have at least one entry so the
                           generator has something actionable to work with
    """

    has_injuries = serializers.BooleanField(
        help_text="True if the user has any injury or movement limitation.",
    )

    injured_areas = serializers.ListField(
        child=serializers.ChoiceField(choices=InjuredArea.choices),
        required=False,
        default=list,   # defaults to [] so the field is always present in validated_data
        help_text=(
            "Body areas with pain or injury. "
            "Allowed: shoulders | elbows | wrists | neck | upper_back | "
            "lower_back | hips | knees | ankles. "
            "Required (non-empty) when has_injuries is true."
        ),
    )

    movements_to_avoid = serializers.ListField(
        child=serializers.ChoiceField(choices=MovementToAvoid.choices),
        required=False,
        default=list,   # defaults to []
        help_text=(
            "Movement patterns to exclude from the program. "
            "Allowed: squatting | lunging | bending | overhead_pressing | "
            "pushing | pulling | jumping | running. "
            "Optional even when has_injuries is true."
        ),
    )

    injury_notes = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Free-text description of the injury or limitation. Optional.",
    )

    def validate_injured_areas(self, value):
        # Remove duplicates; preserve a stable sorted order for consistent responses.
        return sorted(set(value))

    def validate_movements_to_avoid(self, value):
        return sorted(set(value))

    def validate(self, data):
        has_injuries       = data.get("has_injuries")
        injured_areas      = data.get("injured_areas", [])
        movements_to_avoid = data.get("movements_to_avoid", [])
        injury_notes       = data.get("injury_notes") or ""

        if not has_injuries:
            # ── No injuries — all detail fields must be empty ─────────────────
            errors = {}
            if injured_areas:
                errors["injured_areas"] = "Must be empty when has_injuries is false."
            if movements_to_avoid:
                errors["movements_to_avoid"] = "Must be empty when has_injuries is false."
            if injury_notes.strip():
                errors["injury_notes"] = "Must be null or empty when has_injuries is false."
            if errors:
                raise serializers.ValidationError(errors)

        else:
            # ── Has injuries — at least one area is required ──────────────────
            # Without at least one area the generator has no actionable
            # constraint to apply — the user must be more specific.
            if not injured_areas:
                raise serializers.ValidationError(
                    {"injured_areas": "At least one injured area is required when has_injuries is true."}
                )

        return data


# ── Section 7: Exercise Preferences ──────────────────────────────────────────

class SelectedExerciseSerializer(serializers.Serializer):
    """
    Represents a single exercise the user has selected from the exercise database.

    This is intentionally a structured object — NOT a plain string — because
    exercises are resolved from the exercise API/database on the frontend
    before being sent here.  Storing `id` alongside `name` means the AI
    layer and any future workout-storage layer can reference exercises
    unambiguously, even if the user types a name with a spelling variation.

    Fields
    ------
    id             — the exercise's unique identifier in the exercise database (required)
    name           — human-readable name, e.g. "Lat Pulldown"           (required)
    equipment      — e.g. "cable", "barbell", "dumbbell"                (optional)
    primary_muscle — e.g. "lats", "chest", "quads"                      (optional)

    These optional fields are passed through if the exercise API provides them.
    They give the AI richer context when it cross-references liked/disliked
    exercises against the generated program.
    """

    id = serializers.CharField(
        help_text="Unique exercise ID from the exercise database.",
    )
    name = serializers.CharField(
        help_text="Human-readable exercise name, e.g. 'Lat Pulldown'.",
    )
    equipment = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Equipment used, e.g. 'cable', 'barbell', 'bodyweight'. Optional.",
    )
    primary_muscle = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Primary muscle targeted, e.g. 'lats', 'chest'. Optional.",
    )


class ExercisePreferencesSerializer(serializers.Serializer):
    """
    Collects the user's training style and exercise preferences.

    Exercise search flow
    --------------------
    liked_exercises and disliked_exercises are NOT free-text fields.
    The frontend presents a search interface backed by the exercise database.
    The user searches, selects exercises, and the frontend sends back
    structured exercise objects (id + name + optional metadata).

    This serializer accepts and validates those objects.

    Validation summary
    ------------------
    - priority_muscle_groups → deduplicated, sorted; empty list is valid
    - wants_cardio = false   → cardio_preferences must be empty
    - wants_cardio = true    → cardio_preferences may be any subset of allowed values
    - liked/disliked lists   → deduplicated by exercise id (first occurrence wins)
    - cross-list conflict    → same exercise id cannot appear in both lists
    - both lists             → empty lists are valid (selection is optional)
    """

    training_style_preference = serializers.ChoiceField(
        choices=TrainingStylePreference.choices,
        help_text="One of: bodybuilding | powerlifting | general_fitness | no_preference",
    )

    priority_muscle_groups = serializers.ListField(
        child=serializers.ChoiceField(choices=MuscleGroup.choices),
        required=False,
        default=list,
        help_text=(
            "Muscle groups to emphasize with higher volume and frequency. "
            "Allowed: chest | back | shoulders | biceps | triceps | forearms | "
            "abs | glutes | quads | hamstrings | calves. "
            "May be empty — an empty list means balanced volume across all groups."
        ),
    )

    wants_cardio = serializers.BooleanField(
        help_text="Whether the user wants cardio included in their program.",
    )

    cardio_preferences = serializers.ListField(
        child=serializers.ChoiceField(choices=CardioType.choices),
        required=False,
        default=list,
        help_text=(
            "Cardio types the user enjoys. Empty when wants_cardio is false. "
            "Allowed: running | cycling | rowing | walking | stair_climber | "
            "hiit | sports | no_preference"
        ),
    )

    # Each item is a structured exercise object resolved from the exercise database.
    liked_exercises = serializers.ListField(
        child=SelectedExerciseSerializer(),
        required=False,
        default=list,
        help_text=(
            "Exercises the user enjoys, selected from the exercise database. "
            "Each object must contain at least 'id' and 'name'. "
            "Can be empty if the user skips this step."
        ),
    )

    disliked_exercises = serializers.ListField(
        child=SelectedExerciseSerializer(),
        required=False,
        default=list,
        help_text=(
            "Exercises the user dislikes or wants to avoid, selected from the "
            "exercise database. Each object must contain at least 'id' and 'name'. "
            "Can be empty if the user skips this step."
        ),
    )

    def validate_priority_muscle_groups(self, value):
        # Remove duplicates; sort for a stable, consistent response.
        return sorted(set(value))

    def validate_cardio_preferences(self, value):
        # Deduplicate and sort for a consistent response.
        return sorted(set(value))

    @staticmethod
    def _dedup_exercises(exercise_list):
        """
        Remove duplicate exercise objects by id.
        First occurrence wins — later duplicates are dropped silently.
        Returns a new list preserving insertion order of unique items.
        """
        seen = {}
        for ex in exercise_list:
            ex_id = ex.get("id")
            if ex_id not in seen:
                seen[ex_id] = ex
        return list(seen.values())

    def validate(self, data):
        wants_cardio       = data.get("wants_cardio")
        cardio_preferences = data.get("cardio_preferences", [])
        liked              = data.get("liked_exercises", [])
        disliked           = data.get("disliked_exercises", [])

        # ── Cardio consistency ────────────────────────────────────────────────
        if not wants_cardio and cardio_preferences:
            raise serializers.ValidationError(
                {"cardio_preferences": "Must be empty when wants_cardio is false."}
            )

        # ── Deduplicate each list by exercise id ──────────────────────────────
        data["liked_exercises"]    = self._dedup_exercises(liked)
        data["disliked_exercises"] = self._dedup_exercises(disliked)

        # ── Cross-list conflict: same id cannot appear in both lists ──────────
        liked_ids    = {ex["id"] for ex in data["liked_exercises"]}
        disliked_ids = {ex["id"] for ex in data["disliked_exercises"]}
        conflicts    = liked_ids & disliked_ids

        if conflicts:
            raise serializers.ValidationError(
                {
                    "disliked_exercises": (
                        f"The following exercise IDs appear in both liked_exercises "
                        f"and disliked_exercises: {sorted(conflicts)}. "
                        f"An exercise cannot be both liked and disliked."
                    )
                }
            )

        return data


# ── Section 8: Adherence / Motivation ────────────────────────────────────────

class AdherenceProfileSerializer(serializers.Serializer):
    """
    Collects the user's motivation level, main obstacle, intensity preference,
    and accountability style.

    How each field influences the generated program
    -----------------------------------------------
    motivation_level
        Calibrates overall program ambition and progression speed.
        low      → simple structure, short sessions, habit-building focus
        moderate → standard progressive overload, balanced variety
        high     → higher volume, faster progression, more complex programming

    biggest_obstacle
        Shapes the program to reduce the user's primary source of friction.
        time        → supersets, circuits, sessions ≤ 45 min
        motivation  → exercise variety, milestone goals, engaging formats
        energy      → lower RPE targets, extended warm-up/cool-down
        injuries    → conservative loading, movement substitutions
        knowledge   → simpler exercises, form-focused cues
        consistency → flexible scheduling, low minimum-commitment structure

    preferred_workout_intensity
        Sets the target effort level for individual sessions.
        easy     → lower RPE (≤ 6), longer rest, beginner-friendly loads
        moderate → standard RPE (7–8), normal rest periods
        hard     → high RPE (8–9+), shorter rest, near-maximal intensity

    accountability_preference
        Determines what support features the program should surface.
        none                    → no extras
        reminders               → session reminder notifications
        progress_tracking       → logs, streaks, PR highlights
        coaching_style_feedback → detailed per-session performance feedback
    """

    motivation_level = serializers.ChoiceField(
        choices=MotivationLevel.choices,
        help_text="One of: low | moderate | high",
    )

    biggest_obstacle = serializers.ChoiceField(
        choices=BiggestObstacle.choices,
        help_text=(
            "The user's primary barrier to training consistently. "
            "One of: time | motivation | energy | injuries | knowledge | consistency"
        ),
    )

    preferred_workout_intensity = serializers.ChoiceField(
        choices=WorkoutIntensity.choices,
        help_text="Preferred session difficulty. One of: easy | moderate | hard",
    )

    accountability_preference = serializers.ChoiceField(
        choices=AccountabilityPreference.choices,
        help_text=(
            "How the user prefers to stay accountable. "
            "One of: none | reminders | progress_tracking | coaching_style_feedback"
        ),
    )


# ── Top-level Quiz Serializer ─────────────────────────────────────────────────

class QuizSerializer(serializers.Serializer):
    """
    The master serializer that composes all quiz sections.

    Each section is a nested serializer field.
    To add a new section (e.g. equipment):
        1. Build EquipmentSerializer above.
        2. Add:  equipment = EquipmentSerializer()
        3. Done — DRF handles nesting, validation, and error reporting automatically.

    Cross-section validation (e.g. goal affects equipment recommendations)
    belongs in this class's validate() method.
    """

    # ── Section 1: Goal ───────────────────────────────────────────────────────
    goal = serializers.ChoiceField(
        choices=GoalChoice.choices,
    )
    goal_other_text = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    goal_details = GoalDetailsSerializer()

    # ── Section 2: Training Availability ─────────────────────────────────────
    training_availability = TrainingAvailabilitySerializer()

    # ── Section 3: Training Experience ───────────────────────────────────────
    training_experience = TrainingExperienceSerializer()

    # ── Section 4: Equipment Access ───────────────────────────────────────────
    equipment_access = EquipmentAccessSerializer()

    # ── Section 5: Body + Recovery Context ───────────────────────────────────
    body_recovery_context = BodyRecoveryContextSerializer()

    # ── Section 6: Injuries / Limitations ────────────────────────────────────
    injury_limitations = InjuryLimitationsSerializer()

    # ── Section 7: Exercise Preferences ──────────────────────────────────────
    exercise_preferences = ExercisePreferencesSerializer()

    # ── Section 8: Adherence / Motivation ─────────────────────────────────────
    adherence_profile = AdherenceProfileSerializer()

    def validate(self, data):
        goal       = data.get("goal")
        details    = data.get("goal_details") or {}
        current    = details.get("current_weight_kg")
        target     = details.get("target_weight_kg")
        other_text = data.get("goal_other_text") or ""

        # ── "other" requires explanation ──────────────────────────────────────
        if goal == GoalChoice.OTHER and not other_text.strip():
            raise serializers.ValidationError(
                {"goal_other_text": 'Required when goal is "other".'}
            )

        # ── gain / lose require a target weight ───────────────────────────────
        if goal in (GoalChoice.GAIN_WEIGHT, GoalChoice.LOSE_WEIGHT):
            if target is None:
                raise serializers.ValidationError(
                    {"goal_details": {"target_weight_kg": f'Required when goal is "{goal}".'}},
                )

        # ── maintain must NOT have a target weight ────────────────────────────
        if goal == GoalChoice.MAINTAIN and target is not None:
            raise serializers.ValidationError(
                {"goal_details": {"target_weight_kg": 'Must be null when goal is "maintain".'}},
            )

        # ── directional checks ────────────────────────────────────────────────
        if goal == GoalChoice.GAIN_WEIGHT and target is not None and current is not None:
            if target <= current:
                raise serializers.ValidationError(
                    {"goal_details": {"target_weight_kg": "Target weight must be greater than current weight when gaining weight."}}
                )

        if goal == GoalChoice.LOSE_WEIGHT and target is not None and current is not None:
            if target >= current:
                raise serializers.ValidationError(
                    {"goal_details": {"target_weight_kg": "Target weight must be less than current weight when losing weight."}}
                )

        return data
