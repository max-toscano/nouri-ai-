# ──────────────────────────────────────────────────────────────────────────────
# services/programming_rules/split_volume_rules.py  —  workout_quiz
#
# PURPOSE
# -------
# Second module of the programming rules engine.
#
# Accepts a normalized UserWorkoutProfile (or equivalent dict) and derives:
#   - which split structures are viable given the user's schedule
#   - whether a personalized (muscle-priority-driven) split is allowed/preferred
#   - how strongly priority muscles should influence split design
#   - a starting weekly set range per muscle group
#   - a bonus set allocation for priority muscles when time permits
#   - the target RIR (Reps in Reserve) window for all working sets
#   - session length category and permitted split complexity
#   - human-readable planning notes explaining each decision
#
# PIPELINE POSITION
# -----------------
# UserWorkoutProfile
#     → apply_goal_rules()                   (goal_rules.py)
#         → GoalProgrammingProfile
#     → apply_split_volume_rules()           ← THIS FILE
#         → SplitVolumeRulesProfile
#             → apply_injury_rules()         (future)
#             → apply_experience_rules()     (future)
#                 → WorkoutProgrammingContext
#                     → OpenAI prompt builder (future)
#
# IMPORTANT: this module does NOT produce a concrete day-by-day split.
# It produces planning constraints that the split-construction layer (future)
# will use to select and build the actual workout structure.
#
# DESIGN PRINCIPLES
# -----------------
# - Deterministic: same input always produces the same output.
# - No side effects: pure function, no DB or API calls.
# - Output is verbose: every downstream module needs explicit signals.
# - Lookup tables drive the rule logic — changing a rule means editing a table,
#   not hunting through conditional branches.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Output field value constants ──────────────────────────────────────────────

class SplitType:
    FULL_BODY          = "full_body"
    UPPER_LOWER        = "upper_lower"
    ANTERIOR_POSTERIOR = "anterior_posterior"
    PUSH_PULL_LEGS     = "push_pull_legs"


class SplitPriorityBias:
    """
    How strongly priority muscle groups should influence split design.

    none     → no priority muscles; balanced split selection
    low      → minor preference for placing the muscle earlier in the week
    moderate → clear preference; schedule should accommodate the priority muscle
    high     → strong preference; split structure should be chosen or personalised
               specifically to maximise priority muscle frequency and freshness
    """
    NONE     = "none"
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class SessionLengthCategory:
    """
    Bucketed classification of average available session length.

    short  → < 45 min    — time-constrained; volume must be lean
    medium → 45–75 min   — standard; baseline volume targets apply
    long   → > 75 min    — time-rich; allows higher volume and complexity
    """
    SHORT  = "short"
    MEDIUM = "medium"
    LONG   = "long"


class SplitComplexity:
    """
    Permitted structural complexity for the generated split.

    simple   → full body only; single-movement-pattern sessions
    moderate → upper/lower or anterior/posterior; 2-phase structure
    advanced → PPL or fully personalized; high per-session specificity
    """
    SIMPLE   = "simple"
    MODERATE = "moderate"
    ADVANCED = "advanced"


# ── Lookup tables ─────────────────────────────────────────────────────────────

# Allowed split candidates keyed by training days per week.
# 0 and values above 7 are handled via clamping in the helper.
_SPLIT_CANDIDATES_BY_DAYS: dict[int, list[str]] = {
    1: [SplitType.FULL_BODY],
    2: [SplitType.FULL_BODY, SplitType.UPPER_LOWER, SplitType.ANTERIOR_POSTERIOR],
    3: [SplitType.FULL_BODY, SplitType.UPPER_LOWER, SplitType.ANTERIOR_POSTERIOR],
    4: [SplitType.FULL_BODY, SplitType.UPPER_LOWER, SplitType.ANTERIOR_POSTERIOR],
    5: [SplitType.FULL_BODY, SplitType.UPPER_LOWER, SplitType.ANTERIOR_POSTERIOR],
    6: [SplitType.FULL_BODY, SplitType.PUSH_PULL_LEGS,
        SplitType.UPPER_LOWER, SplitType.ANTERIOR_POSTERIOR],
    7: [SplitType.FULL_BODY, SplitType.PUSH_PULL_LEGS,
        SplitType.UPPER_LOWER, SplitType.ANTERIOR_POSTERIOR],
}

# Base weekly working sets per muscle group, keyed by experience level.
# These are the starting targets before time and priority adjustments.
_BASE_WEEKLY_SETS: dict[str, int] = {
    "beginner":     4,
    "intermediate": 5,
    "advanced":     8,
}

# Adjusted (min, max) weekly set range per muscle group.
# Keyed by (experience_level, session_length_category).
# Hard floor = 3, hard ceiling = 10.
_VOLUME_RANGES: dict[tuple[str, str], tuple[int, int]] = {
    ("beginner",     SessionLengthCategory.SHORT):  (3, 4),
    ("beginner",     SessionLengthCategory.MEDIUM): (3, 6),
    ("beginner",     SessionLengthCategory.LONG):   (4, 8),
    ("intermediate", SessionLengthCategory.SHORT):  (3, 5),
    ("intermediate", SessionLengthCategory.MEDIUM): (4, 7),
    ("intermediate", SessionLengthCategory.LONG):   (5, 9),
    ("advanced",     SessionLengthCategory.SHORT):  (3, 6),
    ("advanced",     SessionLengthCategory.MEDIUM): (5, 9),
    ("advanced",     SessionLengthCategory.LONG):   (6, 10),
}

# Additional weekly sets awarded to priority muscle groups when time permits.
# Priority muscles are trained with intentionally higher volume and freshness.
_PRIORITY_SET_BONUS: dict[str, int] = {
    SessionLengthCategory.SHORT:  0,   # no room for bonus sets in short sessions
    SessionLengthCategory.MEDIUM: 1,   # one extra set per priority muscle per week
    SessionLengthCategory.LONG:   2,   # two extra sets per priority muscle per week
}

# Maximum split complexity permitted per session length category and experience.
# Short sessions constrain complexity regardless of experience.
_MAX_COMPLEXITY: dict[tuple[str, str], str] = {
    ("beginner",     SessionLengthCategory.SHORT):  SplitComplexity.SIMPLE,
    ("beginner",     SessionLengthCategory.MEDIUM): SplitComplexity.MODERATE,
    ("beginner",     SessionLengthCategory.LONG):   SplitComplexity.MODERATE,
    ("intermediate", SessionLengthCategory.SHORT):  SplitComplexity.SIMPLE,
    ("intermediate", SessionLengthCategory.MEDIUM): SplitComplexity.MODERATE,
    ("intermediate", SessionLengthCategory.LONG):   SplitComplexity.ADVANCED,
    ("advanced",     SessionLengthCategory.SHORT):  SplitComplexity.MODERATE,
    ("advanced",     SessionLengthCategory.MEDIUM): SplitComplexity.ADVANCED,
    ("advanced",     SessionLengthCategory.LONG):   SplitComplexity.ADVANCED,
}

# RIR (Reps in Reserve) target window applies to all training regardless of other rules.
_TARGET_RIR_MIN = 0
_TARGET_RIR_MAX = 2


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class SplitVolumeRulesProfile:
    """
    Output of the split and volume rules engine.

    Consumed by the split-construction layer and, eventually, the OpenAI
    prompt builder.  Every field is an explicit, named signal — downstream
    modules should never need to re-derive these values from raw quiz data.

    Schedule fields
    ---------------
    training_days_per_week
        Integer count of days the user is available.

    average_available_session_minutes
        Mean session length across available days.

    longest_available_session_minutes
        Longest single session available; useful for placing high-volume
        priority muscle sessions on the most time-rich day.

    available_training_days
        Ordered list of weekday names where the user can train.

    Split selection fields
    ----------------------
    recommended_split_candidates
        Ordered list of split structures that fit the user's schedule.
        The split-construction layer selects from this list.

    personalized_split_allowed
        True when the schedule has enough days (≥ 2) to make a custom
        muscle-group ordering meaningful.

    personalized_split_preferred
        True when priority muscles exist AND days ≥ 3 — strong signal
        to the split-construction layer to build a custom structure.

    split_priority_bias
        How forcefully priority muscles should drive split design:
        none | low | moderate | high

    Priority muscle fields
    ----------------------
    priority_muscle_groups
        Pass-through from the UserWorkoutProfile.

    priority_muscles_should_be_placed_early_in_week
        When True, the split-construction layer must assign the priority
        muscle's primary session to the earliest available training day.

    priority_muscles_should_be_placed_first_in_workout
        When True, priority muscle exercises must open the relevant session
        before any secondary muscle work.

    Volume fields
    -------------
    base_weekly_sets_per_muscle_group
        Starting weekly set target derived from experience level alone,
        before time adjustments.

    adjusted_weekly_set_range_min
        Lower bound of the realistically achievable weekly set range given
        experience and session length.  Never below 3.

    adjusted_weekly_set_range_max
        Upper bound.  Never above 10.

    priority_muscle_weekly_set_bonus
        Additional sets per week that priority muscles receive on top of
        the adjusted range, when session length permits.

    Intensity field
    ---------------
    target_rir_min / target_rir_max
        All working sets should be performed between these RIR values.
        Fixed at 0–2 for this engine version.

    Meta fields
    -----------
    session_length_category
        Bucketed classification: short | medium | long

    split_complexity_allowed
        Maximum structural complexity permitted: simple | moderate | advanced

    planning_notes
        List of human-readable strings explaining the key rule decisions.
        Passed through to the OpenAI prompt so the model understands the
        constraints it must respect.
    """

    # Schedule
    training_days_per_week:              int
    average_available_session_minutes:   Optional[float]
    longest_available_session_minutes:   Optional[int]
    available_training_days:             list

    # Split selection
    recommended_split_candidates:        list
    personalized_split_allowed:          bool
    personalized_split_preferred:        bool
    split_priority_bias:                 str

    # Priority muscles
    priority_muscle_groups:              list
    priority_muscles_should_be_placed_early_in_week:   bool
    priority_muscles_should_be_placed_first_in_workout: bool

    # Volume
    base_weekly_sets_per_muscle_group:   int
    adjusted_weekly_set_range_min:       int
    adjusted_weekly_set_range_max:       int
    priority_muscle_weekly_set_bonus:    int

    # Intensity
    target_rir_min:                      int
    target_rir_max:                      int

    # Meta
    session_length_category:             str
    split_complexity_allowed:            str
    planning_notes:                      list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Returns a plain dict for JSON serialization or downstream consumption."""
        return asdict(self)


# ── Private helpers ───────────────────────────────────────────────────────────

def _classify_session_length(avg_minutes: Optional[float]) -> str:
    """
    Buckets the average session length into short / medium / long.
    If no session data is available, defaults to 'medium' as a safe baseline.
    """
    if avg_minutes is None:
        return SessionLengthCategory.MEDIUM
    if avg_minutes < 45:
        return SessionLengthCategory.SHORT
    if avg_minutes <= 75:
        return SessionLengthCategory.MEDIUM
    return SessionLengthCategory.LONG


def _clamp_days(days: int) -> int:
    """Returns the closest key in _SPLIT_CANDIDATES_BY_DAYS (1–7)."""
    return max(1, min(days, 7))


def _compute_split_priority_bias(
    priority_muscle_groups: list,
    days: int,
) -> str:
    """
    Returns how forcefully priority muscles should drive split design.

    With only 1 training day there is no scheduling flexibility, so even if
    the user has priority muscles the bias is effectively none — the split
    builder cannot rearrange a single session around muscle priority.

    With 2 days there is minimal but real flexibility (e.g. session A focuses
    on the priority muscle first).

    With 3+ days and multiple priority muscles the bias is high: the split
    structure should be chosen or customised specifically to accommodate the
    priority muscle(s).
    """
    if not priority_muscle_groups or days <= 1:
        return SplitPriorityBias.NONE
    muscle_count = len(priority_muscle_groups)
    if days == 2:
        return SplitPriorityBias.LOW
    if days == 3:
        return SplitPriorityBias.LOW if muscle_count == 1 else SplitPriorityBias.MODERATE
    # 4+ days
    return SplitPriorityBias.MODERATE if muscle_count == 1 else SplitPriorityBias.HIGH


def _build_planning_notes(
    days: int,
    session_category: str,
    experience: str,
    priority_muscle_groups: list,
    split_candidates: list,
    personalized_preferred: bool,
    base_sets: int,
    range_min: int,
    range_max: int,
    bonus: int,
) -> list[str]:
    """
    Generates a list of concise, human-readable planning notes that explain
    the key rule decisions made by this module.

    These notes travel with the SplitVolumeRulesProfile all the way to the
    OpenAI prompt builder, where they give the model explicit reasoning to
    work from rather than requiring it to infer constraints from raw numbers.
    """
    notes = []

    # ── Schedule note ─────────────────────────────────────────────────────────
    if days == 1:
        notes.append(
            "User trains 1 day per week. Only full body splits are viable."
        )
    elif days <= 3:
        notes.append(
            f"User trains {days} days per week. Full body and 2-phase splits "
            f"(upper/lower, anterior/posterior) are all viable candidates."
        )
    else:
        candidates_str = ", ".join(split_candidates)
        notes.append(
            f"User trains {days} days per week. Multiple split structures are "
            f"viable: {candidates_str}."
        )

    # ── Session length note ───────────────────────────────────────────────────
    notes.append(
        f"Session length is classified as '{session_category}'. "
        + {
            SessionLengthCategory.SHORT:  "Volume must stay lean to fit within available time.",
            SessionLengthCategory.MEDIUM: "Baseline volume targets are achievable.",
            SessionLengthCategory.LONG:   "Extended session time allows higher volume and complexity.",
        }[session_category]
    )

    # ── Volume note ───────────────────────────────────────────────────────────
    notes.append(
        f"{experience.capitalize()} base volume starts at {base_sets} weekly sets per "
        f"muscle group. Adjusted range for this user: {range_min}–{range_max} sets per "
        f"muscle per week."
    )

    # ── Priority muscle note ──────────────────────────────────────────────────
    if priority_muscle_groups:
        muscles_str = ", ".join(priority_muscle_groups)
        note = (
            f"Priority muscle group(s): {muscles_str}. "
            "These muscles should be placed earlier in the training week and first "
            "within the relevant workout session."
        )
        if bonus > 0:
            note += (
                f" Session length permits {bonus} additional weekly set(s) "
                "for priority muscles."
            )
        else:
            note += " Session length is too short to award bonus sets to priority muscles."
        notes.append(note)

        if personalized_preferred:
            notes.append(
                "A personalized split is preferred for this user. The split-construction "
                "layer should build a structure that directly accommodates the priority "
                "muscle(s) rather than defaulting to a generic template."
            )
    else:
        notes.append(
            "No priority muscle groups selected. Volume will be distributed evenly "
            "across all muscle groups."
        )

    return notes


# ── Public API ────────────────────────────────────────────────────────────────

def apply_split_volume_rules(profile: dict) -> SplitVolumeRulesProfile:
    """
    Derives split and volume planning rules from the normalized workout profile.

    Parameters
    ----------
    profile : dict
        A UserWorkoutProfile dict (from UserWorkoutProfile.to_dict()) or any
        dict containing at minimum:
            training_days_per_week
            average_available_session_minutes
            longest_available_session_minutes
            available_training_days
            training_experience_level
            priority_muscle_groups
            preferred_workout_intensity   (not used yet; reserved for future module)

    Returns
    -------
    SplitVolumeRulesProfile
        Deterministic rule outputs ready for the split-construction layer.

    Raises
    ------
    ValueError
        If training_experience_level is not one of the recognised values.
    """
    # ── Extract inputs ────────────────────────────────────────────────────────
    days             = int(profile.get("training_days_per_week", 0))
    avg_minutes      = profile.get("average_available_session_minutes")
    longest_minutes  = profile.get("longest_available_session_minutes")
    available_days   = profile.get("available_training_days", [])
    experience       = profile.get("training_experience_level", "beginner")
    priority_muscles = profile.get("priority_muscle_groups", [])

    if experience not in _BASE_WEEKLY_SETS:
        raise ValueError(
            f"Unrecognised training_experience_level: '{experience}'. "
            f"Expected one of: {list(_BASE_WEEKLY_SETS.keys())}."
        )

    # ── Classify session length ───────────────────────────────────────────────
    session_category = _classify_session_length(avg_minutes)

    # ── Split candidates ──────────────────────────────────────────────────────
    clamped_days     = _clamp_days(days)
    split_candidates = _SPLIT_CANDIDATES_BY_DAYS[clamped_days]

    # ── Personalized split flags ──────────────────────────────────────────────
    # Personalized splits need ≥ 2 training days to be structurally meaningful.
    personalized_allowed   = days >= 2
    # Preferred when there are actual priority muscles AND enough days to act on them.
    personalized_preferred = bool(priority_muscles) and days >= 3

    # ── Priority bias and muscle placement flags ──────────────────────────────
    split_bias = _compute_split_priority_bias(priority_muscles, days)

    # Priority placement flags are True whenever there is a priority muscle
    # AND at least 2 days to schedule around.
    has_priority_and_flexibility = bool(priority_muscles) and days >= 2
    place_early_in_week      = has_priority_and_flexibility
    place_first_in_workout   = bool(priority_muscles)   # always true if priority exists

    # ── Volume range ──────────────────────────────────────────────────────────
    base_sets            = _BASE_WEEKLY_SETS[experience]
    range_min, range_max = _VOLUME_RANGES[(experience, session_category)]
    bonus_sets           = _PRIORITY_SET_BONUS[session_category]

    # ── Split complexity ──────────────────────────────────────────────────────
    complexity = _MAX_COMPLEXITY[(experience, session_category)]

    # ── Planning notes ────────────────────────────────────────────────────────
    notes = _build_planning_notes(
        days              = days,
        session_category  = session_category,
        experience        = experience,
        priority_muscle_groups = priority_muscles,
        split_candidates  = split_candidates,
        personalized_preferred = personalized_preferred,
        base_sets         = base_sets,
        range_min         = range_min,
        range_max         = range_max,
        bonus             = bonus_sets,
    )

    return SplitVolumeRulesProfile(

        # Schedule
        training_days_per_week             = days,
        average_available_session_minutes  = avg_minutes,
        longest_available_session_minutes  = longest_minutes,
        available_training_days            = available_days,

        # Split selection
        recommended_split_candidates       = split_candidates,
        personalized_split_allowed         = personalized_allowed,
        personalized_split_preferred       = personalized_preferred,
        split_priority_bias                = split_bias,

        # Priority muscles
        priority_muscle_groups                         = priority_muscles,
        priority_muscles_should_be_placed_early_in_week   = place_early_in_week,
        priority_muscles_should_be_placed_first_in_workout = place_first_in_workout,

        # Volume
        base_weekly_sets_per_muscle_group  = base_sets,
        adjusted_weekly_set_range_min      = range_min,
        adjusted_weekly_set_range_max      = range_max,
        priority_muscle_weekly_set_bonus   = bonus_sets,

        # Intensity
        target_rir_min                     = _TARGET_RIR_MIN,
        target_rir_max                     = _TARGET_RIR_MAX,

        # Meta
        session_length_category            = session_category,
        split_complexity_allowed           = complexity,
        planning_notes                     = notes,
    )
