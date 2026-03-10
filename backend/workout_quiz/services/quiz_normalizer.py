# ──────────────────────────────────────────────────────────────────────────────
# services/quiz_normalizer.py  —  workout_quiz
#
# PURPOSE
# -------
# This service sits between the serializer (validation layer) and the AI layer.
# It accepts already-validated quiz data from QuizSerializer.validated_data and
# produces a clean, flat UserWorkoutProfile object ready for OpenAI consumption.
#
# PIPELINE
# --------
# QuizSerializer.validated_data
#     → normalize_quiz_data(validated_data)
#         → UserWorkoutProfile          (returned as a dataclass)
#             → .to_dict()             (serialized for the API response / AI prompt)
#
# RESPONSIBILITIES
# ----------------
# 1. Flatten deeply-nested structures into top-level fields.
# 2. Compute derived / aggregate values (delta, averages, counts).
# 3. Normalize units (height → cm; already done by serializer, read through here).
# 4. Split exercise objects into parallel id / name lists for easy AI consumption.
# 5. Keep all logic here — serializers only validate, this layer transforms.
#
# NOT RESPONSIBLE FOR
# -------------------
# - Validation   (QuizSerializer handles this)
# - OpenAI calls (future AI service layer handles this)
# - Storage      (future model layer handles this)
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

DAYS_OF_WEEK = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


# ── UserWorkoutProfile dataclass ──────────────────────────────────────────────

@dataclass
class UserWorkoutProfile:
    """
    A flat, normalized representation of the user's full quiz submission.

    This is the single object that moves through the backend after the quiz
    intake is complete.  Every field here is already clean, typed, and
    derived — no further parsing or calculation should be needed downstream.

    Sections
    --------
    Goal             → goal, goal_other_text, weights, weight delta
    Body metrics     → age, sex, height (normalized to cm), sleep, stress, activity
    Availability     → available day list, weekly count, session length stats
    Experience       → level, months, equipment familiarity, compound comfort
    Equipment        → available types, preferred types
    Injuries         → flag, area list, movement exclusions, free-text notes
    Exercise prefs   → training style, priority muscles, cardio, liked/disliked exercises
    Adherence        → motivation, obstacle, intensity, accountability style
    """

    # ── Goal ──────────────────────────────────────────────────────────────────
    goal: str
    goal_other_text: Optional[str]
    current_weight_kg: float
    target_weight_kg: Optional[float]
    goal_weight_delta_kg: Optional[float]   # target − current; negative = weight loss

    # ── Body metrics ──────────────────────────────────────────────────────────
    age: int
    sex: str
    normalized_height_cm: float             # always in cm regardless of input unit
    sleep_hours: float
    stress_level: str
    activity_level_outside_gym: str

    # ── Training availability ─────────────────────────────────────────────────
    available_training_days: list           # e.g. ["monday", "wednesday", "friday"]
    training_days_per_week: int             # len(available_training_days)
    average_available_session_minutes: Optional[float]
    longest_available_session_minutes: Optional[int]

    # ── Training experience ───────────────────────────────────────────────────
    training_experience_level: str
    months_training_consistently: int
    familiar_with_gym_equipment: bool
    comfortable_with_compound_lifts: bool

    # ── Equipment ─────────────────────────────────────────────────────────────
    available_equipment_types: list
    preferred_equipment_types: list

    # ── Injuries / Limitations ────────────────────────────────────────────────
    has_injuries: bool
    injured_areas: list
    movements_to_avoid: list
    injury_notes: Optional[str]

    # ── Exercise preferences ──────────────────────────────────────────────────
    training_style_preference: str
    priority_muscle_groups: list            # [] means balanced volume
    wants_cardio: bool
    cardio_preferences: list
    liked_exercise_ids: list               # parallel to liked_exercise_names
    liked_exercise_names: list
    disliked_exercise_ids: list            # parallel to disliked_exercise_names
    disliked_exercise_names: list

    # ── Adherence / Motivation ────────────────────────────────────────────────
    motivation_level: str
    biggest_obstacle: str
    preferred_workout_intensity: str
    accountability_preference: str

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Returns a plain dict suitable for JSON serialization or OpenAI prompt building.
        dataclasses.asdict() recursively converts all nested structures.
        """
        return asdict(self)


# ── Private helpers ───────────────────────────────────────────────────────────

def _resolve_height_cm(body: dict) -> float:
    """
    Returns the normalized height in centimetres.

    The serializer already computes and injects `normalized_height_cm` into
    body_recovery_context during its validate() method.  We read that directly.

    A recomputation fallback is included for safety in case this service is
    ever called outside of the normal serializer → normalizer pipeline.
    """
    if "normalized_height_cm" in body:
        return body["normalized_height_cm"]

    # Fallback: recompute from raw fields
    unit = body.get("height_unit_system")
    if unit == "imperial":
        return round((body["height_feet"] * 30.48) + (body["height_inches"] * 2.54), 2)
    return round(float(body["height_cm"]), 2)


def _extract_training_days(
    availability: dict,
) -> tuple[list[str], int, Optional[float], Optional[int]]:
    """
    Iterates over the 7-day availability dict and extracts:
        - available_days       : ordered list of day names where is_available=True
        - days_per_week        : len(available_days)
        - avg_session_minutes  : mean of available_minutes across available days
        - max_session_minutes  : longest single session across available days

    Returns (available_days, days_per_week, avg_session_minutes, max_session_minutes).
    If no days are available, averages and max are None.
    """
    available_days: list[str] = []
    session_minutes: list[int] = []

    for day in DAYS_OF_WEEK:
        day_data = availability.get(day, {})
        if day_data.get("is_available"):
            available_days.append(day)
            minutes = day_data.get("available_minutes")
            if minutes is not None:
                session_minutes.append(minutes)

    days_per_week = len(available_days)
    avg_minutes = (
        round(sum(session_minutes) / len(session_minutes), 1)
        if session_minutes else None
    )
    max_minutes = max(session_minutes) if session_minutes else None

    return available_days, days_per_week, avg_minutes, max_minutes


def _extract_exercises(exercise_list: list) -> tuple[list[str], list[str]]:
    """
    Splits a list of structured exercise objects into two parallel flat lists:
        ids   → ["exercise_101", "exercise_205"]
        names → ["Lat Pulldown", "Dumbbell Bench Press"]

    Keeping them as parallel lists (rather than dicts) makes them easier to
    embed directly in an OpenAI prompt as readable enumerations.
    """
    ids   = [ex["id"]   for ex in exercise_list]
    names = [ex["name"] for ex in exercise_list]
    return ids, names


def _compute_weight_delta(
    current: Optional[float],
    target: Optional[float],
) -> Optional[float]:
    """
    Returns target − current, rounded to 2 decimal places.
    Negative result indicates weight loss goal; positive indicates weight gain.
    Returns None when either weight is absent (goal = "other" or "maintain").
    """
    if current is not None and target is not None:
        return round(target - current, 2)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def normalize_quiz_data(validated_data: dict) -> UserWorkoutProfile:
    """
    Transforms QuizSerializer.validated_data into a UserWorkoutProfile.

    Parameters
    ----------
    validated_data : dict
        The .validated_data dict produced by a successfully-validated
        QuizSerializer instance.  All values are already type-correct
        and business-rule validated.

    Returns
    -------
    UserWorkoutProfile
        A flat, derived, AI-ready representation of the user's quiz answers.
    """
    # ── Unpack top-level sections ─────────────────────────────────────────────
    goal_details  = validated_data.get("goal_details", {})
    body          = validated_data.get("body_recovery_context", {})
    availability  = validated_data.get("training_availability", {})
    experience    = validated_data.get("training_experience", {})
    equipment     = validated_data.get("equipment_access", {})
    injuries      = validated_data.get("injury_limitations", {})
    prefs         = validated_data.get("exercise_preferences", {})
    adherence     = validated_data.get("adherence_profile", {})

    # ── Derived values ────────────────────────────────────────────────────────
    current_weight = goal_details.get("current_weight_kg")
    target_weight  = goal_details.get("target_weight_kg")

    (
        available_days,
        days_per_week,
        avg_session_minutes,
        max_session_minutes,
    ) = _extract_training_days(availability)

    liked_ids,    liked_names    = _extract_exercises(prefs.get("liked_exercises", []))
    disliked_ids, disliked_names = _extract_exercises(prefs.get("disliked_exercises", []))

    # ── Build and return the profile ──────────────────────────────────────────
    return UserWorkoutProfile(

        # Goal
        goal                  = validated_data["goal"],
        goal_other_text       = validated_data.get("goal_other_text"),
        current_weight_kg     = current_weight,
        target_weight_kg      = target_weight,
        goal_weight_delta_kg  = _compute_weight_delta(current_weight, target_weight),

        # Body metrics
        age                         = body["age"],
        sex                         = body["sex"],
        normalized_height_cm        = _resolve_height_cm(body),
        sleep_hours                 = body["sleep_hours"],
        stress_level                = body["stress_level"],
        activity_level_outside_gym  = body["activity_level_outside_gym"],

        # Training availability
        available_training_days          = available_days,
        training_days_per_week           = days_per_week,
        average_available_session_minutes = avg_session_minutes,
        longest_available_session_minutes = max_session_minutes,

        # Training experience
        training_experience_level      = experience["training_experience_level"],
        months_training_consistently   = experience["months_training_consistently"],
        familiar_with_gym_equipment    = experience["familiar_with_gym_equipment"],
        comfortable_with_compound_lifts = experience["comfortable_with_compound_lifts"],

        # Equipment
        available_equipment_types = equipment.get("available_equipment_types", []),
        preferred_equipment_types = equipment.get("preferred_equipment_types", []),

        # Injuries
        has_injuries       = injuries.get("has_injuries", False),
        injured_areas      = injuries.get("injured_areas", []),
        movements_to_avoid = injuries.get("movements_to_avoid", []),
        injury_notes       = injuries.get("injury_notes"),

        # Exercise preferences
        training_style_preference = prefs["training_style_preference"],
        priority_muscle_groups    = prefs.get("priority_muscle_groups", []),
        wants_cardio              = prefs["wants_cardio"],
        cardio_preferences        = prefs.get("cardio_preferences", []),
        liked_exercise_ids        = liked_ids,
        liked_exercise_names      = liked_names,
        disliked_exercise_ids     = disliked_ids,
        disliked_exercise_names   = disliked_names,

        # Adherence
        motivation_level          = adherence["motivation_level"],
        biggest_obstacle          = adherence["biggest_obstacle"],
        preferred_workout_intensity = adherence["preferred_workout_intensity"],
        accountability_preference = adherence["accountability_preference"],
    )
