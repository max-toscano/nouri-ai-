# ──────────────────────────────────────────────────────────────────────────────
# services/programming_rules/experience_rules.py  —  workout_quiz
#
# PURPOSE
# -------
# Fourth module of the programming rules engine.
#
# Accepts a normalized UserWorkoutProfile (or equivalent dict) and derives:
#   - weekly set targets per muscle group based on experience level
#   - compound vs isolation lift bias and target ratios
#   - machine vs free-weight bias when no explicit equipment preference exists
#   - exercise complexity ceiling
#   - progression aggressiveness
#   - caution flags for downstream modules
#   - human-readable planning notes
#
# PIPELINE POSITION
# -----------------
# UserWorkoutProfile
#     → apply_goal_rules()              (goal_rules.py)
#         → GoalProgrammingProfile
#     → apply_split_volume_rules()      (split_volume_rules.py)
#         → SplitVolumeRulesProfile
#     → apply_constraint_rules()        (constraint_rules.py)
#         → ConstraintRulesProfile
#     → apply_experience_rules()        ← THIS FILE
#         → ExperienceRulesProfile
#             → WorkoutProgrammingContext  (future — assembles all rule profiles)
#                 → split_builder          (future)
#                 → exercise_selection     (future)
#                 → openai_prompt_builder  (future)
#
# IMPORTANT: this module does NOT generate exercises or workout sessions.
# It produces a rule document that downstream modules must honour when
# selecting exercises, assigning volume, and building splits.
#
# MACHINE/FREE-WEIGHT BIAS NOTE
# ------------------------------
# This module computes a default machine/free-weight bias based on experience
# and comfort signals.  This bias applies ONLY when the user has NOT stated an
# explicit equipment preference.  When preferred_equipment_types is non-empty,
# the constraint_rules module already handles equipment steering via
# equipment_selection_bias — in that case machine_bias and free_weight_bias
# are set to 'none' here to avoid conflicting signals downstream.
#
# DESIGN PRINCIPLES
# -----------------
# - Deterministic: same input always produces the same output.
# - No side effects: pure function, no DB or API calls.
# - Lookup tables drive the baseline rules — changing a rule means editing
#   a table, not hunting through conditional branches.
# - Modifier functions are isolated: each interprets a single user signal
#   and adjusts a specific subset of the output.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ── Output field value constants ──────────────────────────────────────────────
# Defined as module-level classes so downstream modules can reference them
# by name instead of comparing raw strings.
# e.g.  if exp_profile.compound_lift_bias == CompoundBias.HIGH: ...

class CompoundBias:
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class IsolationBias:
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class MachineBias:
    NONE     = "none"
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class FreeWeightBias:
    NONE     = "none"
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class ExerciseComplexity:
    SIMPLE   = "simple"
    MODERATE = "moderate"
    ADVANCED = "advanced"


class ProgressionAggressiveness:
    CONSERVATIVE = "conservative"
    MODERATE     = "moderate"
    AGGRESSIVE   = "aggressive"


# ── Bias rank helpers ─────────────────────────────────────────────────────────
# Three independent rank systems — one per value domain.
# Keeping them separate prevents accidental cross-domain bumping
# (e.g. bumping a complexity level with a machine bias function).

# Machine/Free-weight bias: includes "none" as the floor.
_MACHINE_BIAS_RANK: dict[str, int] = {
    "none":     0,
    "low":      1,
    "moderate": 2,
    "high":     3,
}
_RANK_TO_MACHINE_BIAS: dict[int, str] = {v: k for k, v in _MACHINE_BIAS_RANK.items()}


def _bump_machine_bias_up(level: str, steps: int = 1) -> str:
    """Bumps a machine/free-weight bias level up, capping at 'high'."""
    return _RANK_TO_MACHINE_BIAS[min(_MACHINE_BIAS_RANK.get(level, 0) + steps, 3)]


def _bump_machine_bias_down(level: str, steps: int = 1) -> str:
    """Bumps a machine/free-weight bias level down, flooring at 'none'."""
    return _RANK_TO_MACHINE_BIAS[max(_MACHINE_BIAS_RANK.get(level, 0) - steps, 0)]


# Lift bias (compound / isolation): "none" is not a valid lift bias —
# we always bias toward one or the other, so the floor is "low".
_LIFT_BIAS_RANK: dict[str, int] = {
    "low":      0,
    "moderate": 1,
    "high":     2,
}
_RANK_TO_LIFT_BIAS: dict[int, str] = {v: k for k, v in _LIFT_BIAS_RANK.items()}


def _bump_lift_bias_up(level: str, steps: int = 1) -> str:
    """Bumps a compound/isolation bias level up, capping at 'high'."""
    return _RANK_TO_LIFT_BIAS[min(_LIFT_BIAS_RANK.get(level, 0) + steps, 2)]


def _bump_lift_bias_down(level: str, steps: int = 1) -> str:
    """Bumps a compound/isolation bias level down, flooring at 'low'."""
    return _RANK_TO_LIFT_BIAS[max(_LIFT_BIAS_RANK.get(level, 0) - steps, 0)]


# Exercise complexity: a 3-tier scale with no "none" tier.
_COMPLEXITY_RANK: dict[str, int] = {
    "simple":   0,
    "moderate": 1,
    "advanced": 2,
}
_RANK_TO_COMPLEXITY: dict[int, str] = {v: k for k, v in _COMPLEXITY_RANK.items()}


def _bump_complexity_down(level: str, steps: int = 1) -> str:
    """Bumps a complexity level down, flooring at 'simple'."""
    return _RANK_TO_COMPLEXITY[max(_COMPLEXITY_RANK.get(level, 0) - steps, 0)]


# ── Lookup tables ─────────────────────────────────────────────────────────────
# These tables are the single source of truth for all baseline rule values.
# Changing a baseline means editing a table entry, not touching function logic.

# Weekly set range (min, max) per muscle group, keyed by experience level.
_BASE_WEEKLY_SETS_RANGE: dict[str, tuple[int, int]] = {
    "beginner":     (3, 4),
    "intermediate": (4, 8),
    "advanced":     (6, 10),
}

# Compound vs isolation target ratios by experience level.
# These are guiding biases, not rigid percentages.
_BASE_LIFT_RATIOS: dict[str, dict[str, float]] = {
    "beginner":     {"compound": 0.80, "isolation": 0.20},
    "intermediate": {"compound": 0.40, "isolation": 0.60},
    "advanced":     {"compound": 0.20, "isolation": 0.80},
}

_BASE_COMPOUND_BIAS: dict[str, str] = {
    "beginner":     CompoundBias.HIGH,
    "intermediate": CompoundBias.MODERATE,
    "advanced":     CompoundBias.LOW,
}

_BASE_ISOLATION_BIAS: dict[str, str] = {
    "beginner":     IsolationBias.LOW,
    "intermediate": IsolationBias.MODERATE,
    "advanced":     IsolationBias.HIGH,
}

_BASE_COMPLEXITY: dict[str, str] = {
    "beginner":     ExerciseComplexity.SIMPLE,
    "intermediate": ExerciseComplexity.MODERATE,
    "advanced":     ExerciseComplexity.ADVANCED,
}

_BASE_PROGRESSION: dict[str, str] = {
    "beginner":     ProgressionAggressiveness.CONSERVATIVE,
    "intermediate": ProgressionAggressiveness.MODERATE,
    "advanced":     ProgressionAggressiveness.AGGRESSIVE,
}

# Default machine bias when no explicit equipment preference is given.
# Beginners benefit from the guided range-of-motion that machines provide,
# even without explicitly requesting them.
_BASE_MACHINE_BIAS: dict[str, str] = {
    "beginner":     MachineBias.MODERATE,
    "intermediate": MachineBias.LOW,
    "advanced":     MachineBias.NONE,
}

# Complementary free-weight bias, also applied only when no explicit preference.
_BASE_FREE_WEIGHT_BIAS: dict[str, str] = {
    "beginner":     FreeWeightBias.LOW,
    "intermediate": FreeWeightBias.MODERATE,
    "advanced":     FreeWeightBias.HIGH,
}

# How many percentage points to shift from compound → isolation
# when the user is not comfortable with compound movements.
_COMPOUND_DISCOMFORT_RATIO_SHIFT: float = 0.10


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class ExperienceRulesProfile:
    """
    Output of the training experience rules engine.

    This is a rule document consumed by all downstream modules.  Every field
    is an explicit, named signal — split construction, exercise selection, and
    volume allocation should never need to re-derive these values from raw
    quiz data.

    Pass-through fields
    -------------------
    training_experience_level
        The raw level string: beginner | intermediate | advanced.
        Carried through for traceability.

    months_training_consistently
        Raw month count.  Provides granularity within a level
        (e.g. a 2-month beginner vs a 10-month beginner).

    familiar_with_gym_equipment
        Whether the user knows how standard gym equipment works.
        False = favour guided, simple machine patterns.

    comfortable_with_compound_lifts
        Whether the user is ready for complex multi-joint free movements
        (squat, deadlift, bench press, overhead press, barbell row).
        False = reduce compound emphasis, favour stable/machine variants.

    Volume fields
    -------------
    baseline_weekly_sets_min / baseline_weekly_sets_max
        The recommended weekly set range per muscle group for this experience
        level.  The split-volume module may further narrow this range based on
        session length.  Both are in units of sets per muscle group per week.

    Compound / Isolation fields
    ---------------------------
    compound_lift_bias
        How strongly to bias exercise selection toward compound movements.
        low | moderate | high

    isolation_lift_bias
        How strongly to bias exercise selection toward isolation movements.
        low | moderate | high

    target_compound_ratio
        Guiding fraction of compound exercises per session.
        e.g. 0.80 means ~80% of slot choices should be compound movements.
        Not a hard cap — the exercise selection layer treats this as a bias.

    target_isolation_ratio
        Complement of target_compound_ratio.  Always sums to 1.0 with it.

    Equipment bias fields
    ---------------------
    machine_bias
        How strongly to prefer machine-based exercise variants.
        none | low | moderate | high

        'none' means two things depending on context:
            a) The user has an explicit equipment preference — defer entirely
               to constraint_rules.equipment_selection_bias.
            b) Advanced users where free weights are the default choice.

    free_weight_bias
        How strongly to prefer free-weight exercise variants.
        none | low | moderate | high

        'none' for the same reasons as machine_bias = 'none'.

    Complexity and progression fields
    ----------------------------------
    exercise_complexity_level
        The ceiling on exercise complexity for this user.
        simple | moderate | advanced

        The exercise selection layer must not assign exercises above this level.
        Complexity reflects coordination demand, technique overhead, and
        equipment-specific skill requirements.

    progression_aggressiveness
        How quickly to advance load and volume week-over-week.
        conservative | moderate | aggressive

    Flags and notes
    ---------------
    caution_flags
        Short machine-readable strings that later modules can check.
        Current possible values:
            "user_not_comfortable_with_compound_lifts"
            "user_not_familiar_with_gym_equipment"

    planning_notes
        Human-readable explanations of key rule decisions, included in
        the OpenAI prompt so the model understands the constraints.
    """

    # Pass-through
    training_experience_level:       str
    months_training_consistently:    int
    familiar_with_gym_equipment:     bool
    comfortable_with_compound_lifts: bool

    # Volume
    baseline_weekly_sets_min:        int
    baseline_weekly_sets_max:        int

    # Compound / Isolation
    compound_lift_bias:              str
    isolation_lift_bias:             str
    target_compound_ratio:           float
    target_isolation_ratio:          float

    # Machine / Free weight
    machine_bias:                    str
    free_weight_bias:                str

    # Complexity and progression
    exercise_complexity_level:       str
    progression_aggressiveness:      str

    # Flags and notes
    caution_flags:                   list = field(default_factory=list)
    planning_notes:                  list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Returns a plain dict for JSON serialization or downstream consumption."""
        return asdict(self)


# ── Private helpers — equipment ───────────────────────────────────────────────

def _has_explicit_equipment_preference(profile: dict) -> bool:
    """
    Returns True if the user has stated a preferred_equipment_types list.

    When True, the machine/free-weight bias from this module must be 'none'
    for both fields.  The constraint_rules module already steers exercise
    selection via equipment_selection_bias, and conflicting bias signals from
    two separate modules would create ambiguous downstream behaviour.
    """
    return bool(profile.get("preferred_equipment_types"))


def _equipment_available(profile: dict, equipment_type: str) -> bool:
    """Returns True if the given type appears in available_equipment_types."""
    return equipment_type in set(profile.get("available_equipment_types", []))


# ── Private helpers — modifiers ───────────────────────────────────────────────

def _apply_compound_comfort_modifier(
    compound_bias:   str,
    isolation_bias:  str,
    compound_ratio:  float,
    isolation_ratio: float,
    comfortable:     bool,
) -> tuple[str, str, float, float]:
    """
    Adjusts compound/isolation signals when the user is not comfortable with
    compound movements.

    When not comfortable:
    - compound_bias drops one level (HIGH → MODERATE, MODERATE → LOW, LOW stays LOW)
    - isolation_bias rises one level (LOW → MODERATE, MODERATE → HIGH, HIGH stays HIGH)
    - compound_ratio decreases by _COMPOUND_DISCOMFORT_RATIO_SHIFT (floor: 0.10)
    - isolation_ratio increases by the same amount (ceiling: 0.90)

    The floor/ceiling prevents the ratios from reaching 0.0 or 1.0 — even an
    uncomfortable beginner should still see some compound movements in a stable,
    machine-based form.  The lift selection layer handles the actual exercise
    choice; this module only adjusts the programming bias.
    """
    if comfortable:
        return compound_bias, isolation_bias, compound_ratio, isolation_ratio

    new_compound_bias   = _bump_lift_bias_down(compound_bias)
    new_isolation_bias  = _bump_lift_bias_up(isolation_bias)
    shift               = _COMPOUND_DISCOMFORT_RATIO_SHIFT
    new_compound_ratio  = round(max(compound_ratio  - shift, 0.10), 2)
    new_isolation_ratio = round(min(isolation_ratio + shift, 0.90), 2)

    return new_compound_bias, new_isolation_bias, new_compound_ratio, new_isolation_ratio


def _apply_equipment_familiarity_modifier(
    complexity: str,
    familiar:   bool,
) -> str:
    """
    Reduces exercise complexity when the user is not familiar with gym equipment.

    Unfamiliar users cannot safely self-regulate loading on complex movements or
    navigate equipment-specific setup.  Reducing complexity by one tier ensures
    the exercise selection layer favours guided patterns over free-form ones.

    Complexity floors at 'simple' — we cannot go below the most accessible tier.
    """
    if familiar:
        return complexity
    return _bump_complexity_down(complexity)


def _compute_machine_free_weight_bias(
    experience:               str,
    comfortable_with_compounds: bool,
    familiar_with_equipment:  bool,
    has_explicit_preference:  bool,
    has_machines:             bool,
    has_free_weights:         bool,
) -> tuple[str, str]:
    """
    Determines machine_bias and free_weight_bias.

    When the user has an explicit equipment preference, both outputs are 'none'
    because constraint_rules.equipment_selection_bias already handles steering.

    When no preference exists:
    - Start from the experience-level baseline (beginner = moderate machine bias,
      intermediate = low, advanced = none).
    - Each missing comfort signal bumps machine_bias up one step (independently):
        a) not comfortable with compound lifts  → +1 step (lack of movement skill)
        b) not familiar with gym equipment      → +1 step (lack of equipment knowledge)
    - free_weight_bias is bumped down by the same total number of steps to keep
      the two signals complementary (they always move in opposite directions).
    - If the corresponding equipment type is not in available_equipment_types,
      that bias is nullified to 'none' — no point biasing toward unavailable kit.
    """
    if has_explicit_preference:
        return MachineBias.NONE, FreeWeightBias.NONE

    machine_bias     = _BASE_MACHINE_BIAS[experience]
    free_weight_bias = _BASE_FREE_WEIGHT_BIAS[experience]

    steps_up = 0
    if not comfortable_with_compounds:
        steps_up += 1
    if not familiar_with_equipment:
        steps_up += 1

    if steps_up > 0:
        machine_bias     = _bump_machine_bias_up(machine_bias, steps_up)
        free_weight_bias = _bump_machine_bias_down(free_weight_bias, steps_up)

    # Nullify bias for unavailable equipment types.
    if not has_machines:
        machine_bias = MachineBias.NONE
    if not has_free_weights:
        free_weight_bias = FreeWeightBias.NONE

    return machine_bias, free_weight_bias


# ── Private helpers — flags and notes ─────────────────────────────────────────

def _build_caution_flags(
    comfortable_with_compounds: bool,
    familiar_with_equipment:    bool,
) -> list[str]:
    """
    Emits machine-readable caution flags for signals that downstream modules
    should check before making exercise or loading decisions.
    """
    flags: list[str] = []
    if not comfortable_with_compounds:
        flags.append("user_not_comfortable_with_compound_lifts")
    if not familiar_with_equipment:
        flags.append("user_not_familiar_with_gym_equipment")
    return flags


def _build_planning_notes(
    experience:             str,
    months:                 int,
    comfortable:            bool,
    familiar:               bool,
    compound_bias:          str,
    isolation_bias:         str,
    target_compound_ratio:  float,
    target_isolation_ratio: float,
    machine_bias:           str,
    free_weight_bias:       str,
    complexity:             str,
    progression:            str,
    has_explicit_preference: bool,
) -> list[str]:
    """
    Generates concise, human-readable planning notes explaining the key rule
    decisions made by this module.

    These notes travel with the ExperienceRulesProfile all the way to the
    OpenAI prompt builder, giving the model explicit reasoning to work from.
    """
    notes: list[str] = []
    sets_min, sets_max = _BASE_WEEKLY_SETS_RANGE[experience]

    # ── Volume note ────────────────────────────────────────────────────────
    notes.append(
        f"{experience.capitalize()} level: baseline weekly set target is "
        f"{sets_min}–{sets_max} sets per muscle group. "
        "The split-volume module may further narrow this range based on session length."
    )

    # ── Compound / Isolation note ──────────────────────────────────────────
    notes.append(
        f"Target lift ratio: {int(target_compound_ratio * 100)}% compound / "
        f"{int(target_isolation_ratio * 100)}% isolation. "
        f"Compound bias: {compound_bias}. Isolation bias: {isolation_bias}. "
        "These are guiding programming biases, not rigid per-session counts."
    )

    # ── Compound comfort modifier note ────────────────────────────────────
    if not comfortable:
        notes.append(
            "User is not comfortable with compound lifts. "
            "Compound emphasis is reduced. Prioritize stable, machine-based, or "
            "supported compound patterns before introducing barbell-loaded free movements. "
            "The caution flag 'user_not_comfortable_with_compound_lifts' is active."
        )

    # ── Equipment familiarity modifier note ───────────────────────────────
    if not familiar:
        notes.append(
            "User is not familiar with gym equipment. "
            "Exercise selection should favour simple, guided machine patterns. "
            f"Exercise complexity is capped at '{complexity}'. "
            "The caution flag 'user_not_familiar_with_gym_equipment' is active."
        )

    # ── Machine / Free-weight bias note ───────────────────────────────────
    if has_explicit_preference:
        notes.append(
            "User has an explicit equipment preference. "
            "Machine/free-weight bias from this module is deferred to "
            "constraint_rules.equipment_selection_bias — no conflict."
        )
    else:
        notes.append(
            f"No explicit equipment preference set. "
            f"Defaulting to machine_bias='{machine_bias}', "
            f"free_weight_bias='{free_weight_bias}' "
            f"based on experience level and comfort signals."
        )

    # ── Progression note ──────────────────────────────────────────────────
    progression_explanation = {
        ProgressionAggressiveness.CONSERVATIVE: (
            "Use longer adaptation phases. Prioritise movement quality and "
            "consistent habit formation over rapid load increases."
        ),
        ProgressionAggressiveness.MODERATE: (
            "Apply standard linear or block periodization. "
            "Progressive overload should drive weekly adaptation."
        ),
        ProgressionAggressiveness.AGGRESSIVE: (
            "Shorter mesocycles, faster overload targets, near-maximal effort. "
            "Variation and deload timing are critical to avoid stagnation."
        ),
    }
    notes.append(
        f"Progression aggressiveness: {progression}. "
        + progression_explanation[progression]
    )

    # ── Training tenure note ──────────────────────────────────────────────
    if months < 6:
        notes.append(
            f"User has {months} month(s) of consistent training. "
            "Prioritise movement quality and habit formation. "
            "Volume should start at the lower end of the baseline range."
        )
    elif months < 24:
        notes.append(
            f"User has {months} months of consistent training. "
            "Progressive overload is the primary adaptation driver. "
            "Volume can track toward the upper end of the baseline range."
        )
    else:
        notes.append(
            f"User has {months} months of consistent training. "
            "Periodization and exercise variation are important to continue "
            "driving adaptations at this training age."
        )

    return notes


# ── Public API ────────────────────────────────────────────────────────────────

def apply_experience_rules(profile: dict) -> ExperienceRulesProfile:
    """
    Derives training experience rules from the normalized workout profile.

    Parameters
    ----------
    profile : dict
        A UserWorkoutProfile dict (from UserWorkoutProfile.to_dict()) or any
        dict containing at minimum:
            training_experience_level        — "beginner" | "intermediate" | "advanced"
            months_training_consistently     — integer ≥ 0
            familiar_with_gym_equipment      — bool
            comfortable_with_compound_lifts  — bool
            available_equipment_types        — list of equipment type strings
            preferred_equipment_types        — list of equipment type strings (may be empty)

    Returns
    -------
    ExperienceRulesProfile
        A deterministic rule document ready for split construction,
        exercise selection, and volume allocation modules.

    Raises
    ------
    ValueError
        If training_experience_level is not one of the recognised values.
        This should never happen in production (the serializer enforces the
        allowed values) but the explicit check guards against direct calls.
    """
    # ── Extract inputs ────────────────────────────────────────────────────────
    experience  = profile.get("training_experience_level", "beginner")
    months      = int(profile.get("months_training_consistently", 0))
    familiar    = bool(profile.get("familiar_with_gym_equipment", False))
    comfortable = bool(profile.get("comfortable_with_compound_lifts", False))

    if experience not in _BASE_WEEKLY_SETS_RANGE:
        raise ValueError(
            f"Unrecognised training_experience_level: '{experience}'. "
            f"Expected one of: {list(_BASE_WEEKLY_SETS_RANGE.keys())}."
        )

    # ── Volume range ──────────────────────────────────────────────────────────
    sets_min, sets_max = _BASE_WEEKLY_SETS_RANGE[experience]

    # ── Compound / Isolation — start from baseline ────────────────────────────
    compound_bias   = _BASE_COMPOUND_BIAS[experience]
    isolation_bias  = _BASE_ISOLATION_BIAS[experience]
    base_ratios     = _BASE_LIFT_RATIOS[experience]
    compound_ratio  = base_ratios["compound"]
    isolation_ratio = base_ratios["isolation"]

    # Apply compound comfort modifier.
    (
        compound_bias,
        isolation_bias,
        compound_ratio,
        isolation_ratio,
    ) = _apply_compound_comfort_modifier(
        compound_bias,
        isolation_bias,
        compound_ratio,
        isolation_ratio,
        comfortable,
    )

    # ── Exercise complexity ───────────────────────────────────────────────────
    # Start from the experience baseline, then reduce if the user is not
    # familiar with equipment (each is an independent signal).
    complexity = _apply_equipment_familiarity_modifier(
        _BASE_COMPLEXITY[experience],
        familiar,
    )

    # ── Progression aggressiveness ────────────────────────────────────────────
    # Experience level sets the baseline; no further modifiers at this stage.
    # Future modules (goal_rules integration) may adjust this.
    progression = _BASE_PROGRESSION[experience]

    # ── Machine / Free-weight bias ────────────────────────────────────────────
    has_explicit_preference = _has_explicit_equipment_preference(profile)
    has_machines     = _equipment_available(profile, "machines")
    has_free_weights = _equipment_available(profile, "free_weights")

    machine_bias, free_weight_bias = _compute_machine_free_weight_bias(
        experience               = experience,
        comfortable_with_compounds = comfortable,
        familiar_with_equipment  = familiar,
        has_explicit_preference  = has_explicit_preference,
        has_machines             = has_machines,
        has_free_weights         = has_free_weights,
    )

    # ── Caution flags ─────────────────────────────────────────────────────────
    caution_flags = _build_caution_flags(comfortable, familiar)

    # ── Planning notes ────────────────────────────────────────────────────────
    notes = _build_planning_notes(
        experience              = experience,
        months                  = months,
        comfortable             = comfortable,
        familiar                = familiar,
        compound_bias           = compound_bias,
        isolation_bias          = isolation_bias,
        target_compound_ratio   = compound_ratio,
        target_isolation_ratio  = isolation_ratio,
        machine_bias            = machine_bias,
        free_weight_bias        = free_weight_bias,
        complexity              = complexity,
        progression             = progression,
        has_explicit_preference = has_explicit_preference,
    )

    return ExperienceRulesProfile(

        # Pass-through
        training_experience_level       = experience,
        months_training_consistently    = months,
        familiar_with_gym_equipment     = familiar,
        comfortable_with_compound_lifts = comfortable,

        # Volume
        baseline_weekly_sets_min        = sets_min,
        baseline_weekly_sets_max        = sets_max,

        # Compound / Isolation
        compound_lift_bias              = compound_bias,
        isolation_lift_bias             = isolation_bias,
        target_compound_ratio           = compound_ratio,
        target_isolation_ratio          = isolation_ratio,

        # Machine / Free weight
        machine_bias                    = machine_bias,
        free_weight_bias                = free_weight_bias,

        # Complexity and progression
        exercise_complexity_level       = complexity,
        progression_aggressiveness      = progression,

        # Flags and notes
        caution_flags                   = caution_flags,
        planning_notes                  = notes,
    )
