# ──────────────────────────────────────────────────────────────────────────────
# services/programming_rules/goal_rules.py  —  workout_quiz
#
# PURPOSE
# -------
# First module of the programming rules engine.
#
# Accepts a normalized UserWorkoutProfile (or equivalent dict) and interprets
# the user's fitness goal into a set of training-rule outputs.
#
# These outputs are consumed by later modules in the programming rules engine
# (frequency, volume, experience, injury, split selection) and ultimately
# assembled into the context that OpenAI uses to generate the workout plan.
#
# PIPELINE POSITION
# -----------------
# UserWorkoutProfile
#     → apply_goal_rules()      ← THIS FILE
#         → GoalProgrammingProfile
#             → apply_frequency_rules()    (future)
#             → apply_experience_rules()   (future)
#             → apply_injury_rules()       (future)
#             → apply_split_rules()        (future)
#                 → WorkoutProgrammingContext
#                     → OpenAI prompt builder (future)
#
# DESIGN PRINCIPLES
# -----------------
# - Deterministic: same input always produces the same output.
# - No side effects: pure function, no DB or API calls.
# - Modifiable without touching other modules: each rules file is self-contained.
# - Output is deliberately verbose: downstream modules need explicit signals,
#   not values they have to infer or re-derive.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


# ── Output field value constants ──────────────────────────────────────────────
# Defined as module-level strings so downstream modules can reference them
# by name instead of comparing raw strings.
# e.g.  if goal_profile.goal_direction == GoalDirection.CUT: ...

class GoalDirection:
    CUT      = "cut"
    BULK     = "bulk"
    MAINTAIN = "maintain"
    CUSTOM   = "custom"


class ProgramBias:
    FAT_LOSS_WITH_MUSCLE_RETENTION = "fat_loss_with_muscle_retention"
    HYPERTROPHY                    = "hypertrophy"
    BALANCED_FITNESS               = "balanced_fitness"
    GENERAL_FITNESS                = "general_fitness"


class CardioEmphasis:
    NONE     = "none"       # user explicitly opted out of cardio
    LOW      = "low"        # cardio present but minimal
    OPTIONAL = "optional"   # include if user wants it, not a programming priority
    HIGH     = "high"       # cardio is a core component of the program


class LiftingEmphasis:
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class ProgressionBias:
    STEADY      = "steady"      # standard linear or undulating progression
    AGGRESSIVE  = "aggressive"  # faster overload, shorter deload cycles


class RecoveryBias:
    NORMAL        = "normal"         # standard rest periods and deload frequency
    HIGH_PRIORITY = "high_priority"  # extended rest, earlier deloads, more sleep cues


# ── Base rules table ──────────────────────────────────────────────────────────
# Maps each goal value to its default programming rule outputs.
# These are applied first; modifiers below may override specific fields.

_BASE_GOAL_RULES: dict[str, dict] = {
    "lose_weight": {
        "goal_direction":   GoalDirection.CUT,
        "program_bias":     ProgramBias.FAT_LOSS_WITH_MUSCLE_RETENTION,
        "cardio_emphasis":  CardioEmphasis.HIGH,
        "lifting_emphasis": LiftingEmphasis.MODERATE,
        "progression_bias": ProgressionBias.STEADY,
        "recovery_bias":    RecoveryBias.NORMAL,
    },
    "gain_weight": {
        "goal_direction":   GoalDirection.BULK,
        "program_bias":     ProgramBias.HYPERTROPHY,
        "cardio_emphasis":  CardioEmphasis.LOW,
        "lifting_emphasis": LiftingEmphasis.HIGH,
        "progression_bias": ProgressionBias.AGGRESSIVE,
        "recovery_bias":    RecoveryBias.HIGH_PRIORITY,
    },
    "maintain": {
        "goal_direction":   GoalDirection.MAINTAIN,
        "program_bias":     ProgramBias.BALANCED_FITNESS,
        "cardio_emphasis":  CardioEmphasis.OPTIONAL,
        "lifting_emphasis": LiftingEmphasis.MODERATE,
        "progression_bias": ProgressionBias.STEADY,
        "recovery_bias":    RecoveryBias.NORMAL,
    },
    "other": {
        "goal_direction":   GoalDirection.CUSTOM,
        "program_bias":     ProgramBias.GENERAL_FITNESS,
        "cardio_emphasis":  CardioEmphasis.OPTIONAL,
        "lifting_emphasis": LiftingEmphasis.MODERATE,
        "progression_bias": ProgressionBias.STEADY,
        "recovery_bias":    RecoveryBias.NORMAL,
    },
}


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class GoalProgrammingProfile:
    """
    The output of the goal rules engine.

    Downstream modules (frequency, volume, experience, injury, split) read
    these fields to make their own rule decisions.  The full set of outputs
    from all modules is eventually assembled into a WorkoutProgrammingContext
    that the OpenAI prompt builder will consume.

    Fields
    ------
    primary_goal
        The raw goal string from the user's quiz ("lose_weight", "gain_weight",
        "maintain", "other").  Passed through unchanged for traceability.

    goal_direction
        High-level direction of the program: cut | bulk | maintain | custom.
        Used by the split and volume modules to decide total weekly structure.

    goal_weight_delta_kg
        Numeric weight change target (negative = loss, positive = gain).
        None when goal is "maintain" or "other".
        Used by future modules to scale aggressiveness of the program.

    program_bias
        The dominant programming philosophy:
            fat_loss_with_muscle_retention → caloric-deficit-compatible training
            hypertrophy                    → volume and progressive overload focus
            balanced_fitness               → mixed modalities, no single emphasis
            general_fitness                → sensible defaults, user-directed

    cardio_emphasis
        How prominently cardio features in the program:
            none     → user opted out; no cardio blocks in the plan
            low      → 1 light session per week maximum
            optional → include only if the user selected cardio types
            high     → 2–3 dedicated cardio sessions per week

    lifting_emphasis
        Relative importance of resistance training in the plan:
            low      → rare (not currently assigned by any goal rule)
            moderate → balanced resistance work, not the sole focus
            high     → resistance training is the primary driver

    progression_bias
        How quickly to advance loading week-over-week:
            steady     → standard linear/undulating progression, normal deloads
            aggressive → shorter mesocycles, faster overload, earlier PRs targeted

    recovery_bias
        How much the plan should prioritize rest and recovery signalling:
            normal        → standard rest periods, every-4th-week deload
            high_priority → extended inter-set rest, earlier deloads, sleep cues

    custom_goal_notes
        The user's free-text explanation when goal = "other".
        Passed through to the OpenAI prompt so the AI understands the intent.
        None for all other goal types.
    """

    primary_goal:          str
    goal_direction:        str
    goal_weight_delta_kg:  Optional[float]
    program_bias:          str
    cardio_emphasis:       str
    lifting_emphasis:      str
    progression_bias:      str
    recovery_bias:         str
    custom_goal_notes:     Optional[str]

    def to_dict(self) -> dict:
        """Returns a plain dict for JSON serialization or downstream consumption."""
        return asdict(self)


# ── Modifiers ─────────────────────────────────────────────────────────────────

def _apply_cardio_modifier(rules: dict, profile: dict) -> None:
    """
    Overrides cardio_emphasis when the user has explicitly opted out of cardio.

    The base rules table sets cardio_emphasis based purely on the fitness goal.
    But if wants_cardio = False the user has made a direct preference decision
    that overrides the goal-based default.

    This is applied here (rather than in a separate preferences module) because
    cardio_emphasis is a GoalProgrammingProfile field — it belongs to this
    module's output contract.  The value "none" signals to all downstream
    modules that cardio blocks must not appear in the generated plan.
    """
    if not profile.get("wants_cardio", True):
        rules["cardio_emphasis"] = CardioEmphasis.NONE


# ── Public API ────────────────────────────────────────────────────────────────

def apply_goal_rules(profile: dict) -> GoalProgrammingProfile:
    """
    Interprets the user's fitness goal and returns a GoalProgrammingProfile.

    Parameters
    ----------
    profile : dict
        A UserWorkoutProfile dict (from UserWorkoutProfile.to_dict()) or any
        dict that contains at minimum the keys:
            goal, goal_weight_delta_kg, wants_cardio, goal_other_text

    Returns
    -------
    GoalProgrammingProfile
        Deterministic rule outputs derived from the goal and relevant modifiers.

    Raises
    ------
    ValueError
        If `goal` is missing or not one of the four recognised values.
        This should never happen in production because the serializer enforces
        the allowed values — but the explicit check guards against direct calls.
    """
    goal = profile.get("goal")

    if goal not in _BASE_GOAL_RULES:
        raise ValueError(
            f"Unrecognised goal value: '{goal}'. "
            f"Expected one of: {list(_BASE_GOAL_RULES.keys())}."
        )

    # Start with a mutable copy of the base rules for this goal.
    rules = dict(_BASE_GOAL_RULES[goal])

    # Apply modifiers that may override individual fields.
    _apply_cardio_modifier(rules, profile)

    # custom_goal_notes is only populated when goal = "other".
    custom_notes = (
        profile.get("goal_other_text")
        if goal == "other"
        else None
    )

    return GoalProgrammingProfile(
        primary_goal         = goal,
        goal_direction       = rules["goal_direction"],
        goal_weight_delta_kg = profile.get("goal_weight_delta_kg"),
        program_bias         = rules["program_bias"],
        cardio_emphasis      = rules["cardio_emphasis"],
        lifting_emphasis     = rules["lifting_emphasis"],
        progression_bias     = rules["progression_bias"],
        recovery_bias        = rules["recovery_bias"],
        custom_goal_notes    = custom_notes,
    )
