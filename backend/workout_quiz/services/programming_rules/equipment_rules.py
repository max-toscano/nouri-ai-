# ──────────────────────────────────────────────────────────────────────────────
# services/programming_rules/equipment_rules.py  —  workout_quiz
#
# PURPOSE
# -------
# Fifth module of the programming rules engine.
#
# Converts the user's equipment access and preference answers into a
# deterministic EquipmentConstraintProfile that downstream modules consume
# for exercise filtering, selection bias, and split construction.
#
# RELATIONSHIP TO constraint_rules.py
# ------------------------------------
# constraint_rules.py handles equipment at a high level alongside injury data:
#   - allowed_exercise_modalities  (label strings)
#   - discouraged_exercise_modalities
#   - equipment_selection_bias     (string level: none|low|moderate|high)
#
# This module goes deeper on equipment specifically:
#   - selection_bias as numeric float weights per equipment type (sums to 1.0)
#   - hard boolean constraint flags per equipment type
#   - explicit fallback logic when a stated preference is unavailable
#   - caution flags for downstream modules
#
# Both modules are composed into the future WorkoutProgrammingContext.
# They are not duplicates — they operate at different levels of granularity.
#
# PIPELINE POSITION
# -----------------
# UserWorkoutProfile
#     → apply_goal_rules()              (goal_rules.py)
#     → apply_split_volume_rules()      (split_volume_rules.py)
#     → apply_constraint_rules()        (constraint_rules.py)
#     → apply_experience_rules()        (experience_rules.py)
#     → apply_equipment_rules()         ← THIS FILE
#         → EquipmentConstraintProfile
#             → WorkoutProgrammingContext  (future)
#                 → split_builder
#                 → exercise_selection_engine
#                 → openai_prompt_builder
#
# IMPORTANT: this module does NOT generate exercises or workouts.
# It produces a constraint document that exercise selection must honour.
#
# DESIGN PRINCIPLES
# -----------------
# - Deterministic: same input always produces the same output.
# - No side effects: pure function, no DB or API calls.
# - Lookup tables drive weight calculations — changing a rule means editing
#   a table row, not hunting through conditional branches.
# - Conservative by default: if equipment data is missing or ambiguous,
#   default to the most permissive safe fallback (bodyweight).
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Known equipment types ─────────────────────────────────────────────────────
# Single source of truth for all valid equipment type strings.
# The serializer (quiz_choices.EquipmentType) enforces these values at intake.
# This constant is used here for validation when the module is called directly
# (bypassing the serializer) in unit tests or future service integrations.

KNOWN_EQUIPMENT_TYPES: frozenset[str] = frozenset({
    "machines",
    "free_weights",
    "bodyweight",
})

# Fallback equipment type used when no access data is provided.
# Bodyweight requires no external equipment and is always physically available
# to the user regardless of location, so it is the safest default.
_FALLBACK_EQUIPMENT = "bodyweight"


# ── Selection bias weight table ───────────────────────────────────────────────
# Maps (n_allowed_total, n_effective_preferred) to the total weight share
# allocated to the preferred group and to the non-preferred group.
#
# Weights within each group are distributed equally among its members:
#   preferred_each   = preferred_group_share  / n_effective_preferred
#   non_pref_each    = non_preferred_group_share / (n_allowed - n_effective_preferred)
#
# Design intent:
#   - When n_effective_preferred == 0 (no preference):
#       equal distribution across all allowed types.
#   - When n_effective_preferred == n_allowed (all types are preferred):
#       equal distribution (preference has no discriminating power).
#   - Otherwise, preferred types receive a meaningful but not absolute boost.
#     The non-preferred share (≥ 0.30) ensures those types remain selectable —
#     this is a bias, not a hard exclusion.
#
#   Key      (n_total, n_preferred) → (preferred_share, non_preferred_share)
_PREFERENCE_ALLOCATION: dict[tuple[int, int], tuple[float, float]] = {
    (1, 1): (1.0000, 0.0000),   # only 1 type and it's preferred — 100% weight
    (2, 1): (0.7000, 0.3000),   # prefer 1 of 2: 70 / 30
    (2, 2): (1.0000, 0.0000),   # prefer both of 2: equal (same as no preference)
    (3, 1): (0.6000, 0.4000),   # prefer 1 of 3: 60 / 20 / 20
    (3, 2): (0.7000, 0.3000),   # prefer 2 of 3: 35 / 35 / 30
    (3, 3): (1.0000, 0.0000),   # prefer all 3: equal (same as no preference)
}


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class EquipmentConstraintProfile:
    """
    Output of the equipment constraint rules engine.

    This is a constraint document — not a workout.  Every downstream module
    (split construction, exercise selection, OpenAI prompt builder) must
    consult this profile before making an equipment-related decision.

    Access fields
    -------------
    allowed_equipment
        The equipment types the user actually has access to.
        Exercise selection MUST stay within this list.
        This is the hard filter — nothing outside it is permitted.

    equipment_access_map
        A {type: bool} dict for quick lookup by type name.
        Downstream modules can do:  if profile.equipment_access_map["machines"]
        instead of: if "machines" in profile.allowed_equipment

    Preference fields
    -----------------
    requested_preferred_equipment
        The equipment types the user stated as preferred (raw from quiz).
        This may include types that are not in allowed_equipment if the module
        was called directly (bypassing the serializer).  The serializer enforces
        preferred ⊆ available, so in production this will always be a subset of
        allowed_equipment — but we capture and validate here for safety.

    effective_preferred_equipment
        The actionable preference list: requested_preferred filtered to those
        that are actually in allowed_equipment.
        This is what downstream modules should use for selection bias.

    unavailable_preference
        Preferred types that were requested but are NOT in allowed_equipment.
        In production (serializer-validated data) this will always be empty.
        Populated only when the module is called directly with inconsistent data
        (e.g. in unit tests simulating invalid input).

    preference_satisfied
        True when every requested preference is available (unavailable_preference
        is empty).  False when any preference had to be dropped.

    fallback_triggered
        True when unavailable_preference is non-empty AND
        effective_preferred_equipment ended up empty (no preference is actionable).
        In this case the module fell back to the full allowed_equipment list
        as the effective preference (no bias applied).

    no_equipment_fallback
        True when allowed_equipment was empty and the module defaulted to
        ["bodyweight"].  This should not happen in production (the serializer
        requires at least one equipment type) but is handled defensively.

    Selection bias fields
    ---------------------
    selection_bias
        A {equipment_type: float} dict where weights sum to 1.0 (across the
        allowed types).  Exercise selection uses these weights to rank candidate
        exercises from each equipment category.

        When there is no effective preference, all allowed types receive equal
        weight (1 / n_allowed).

        When there is a preference, preferred types receive a higher share
        (see _PREFERENCE_ALLOCATION) — this is a BIAS, not a hard exclusion.
        Non-preferred types remain selectable with a lower weight.

    Hard constraint fields
    ----------------------
    hard_constraints
        A {flag: bool} dict that downstream modules check as quick conditionals.
        All flags relate to access restrictions, not preference signals.

        exclude_unavailable_equipment
            Always True.  The core rule: never assign exercises that require
            equipment the user does not have access to.

        single_modality_only
            True when only one equipment type is available.  The exercise
            selection layer must draw all exercises from that single type.

        machines_excluded
            True when "machines" is not in allowed_equipment.

        free_weights_excluded
            True when "free_weights" is not in allowed_equipment.

        bodyweight_excluded
            True when "bodyweight" is not in allowed_equipment.
            Note: the split-builder should still allow minimal bodyweight warmup
            movements (unloaded mobility, planks) even when this flag is True,
            since these require no equipment.  Only scored/programmed bodyweight
            sessions should be blocked.

    Meta fields
    -----------
    caution_flags
        Short machine-readable strings for downstream modules to check.

    planning_notes
        Human-readable explanations of key rule decisions, included in the
        OpenAI prompt so the model understands the equipment context.
    """

    # Access
    allowed_equipment:         list[str]
    equipment_access_map:      dict[str, bool]

    # Preference
    requested_preferred_equipment:  list[str]
    effective_preferred_equipment:  list[str]
    unavailable_preference:         list[str]
    preference_satisfied:           bool
    fallback_triggered:             bool
    no_equipment_fallback:          bool

    # Selection bias
    selection_bias:            dict[str, float]

    # Hard constraints
    hard_constraints:          dict[str, bool]

    # Meta
    caution_flags:             list[str] = field(default_factory=list)
    planning_notes:            list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Returns a plain dict for JSON serialization or downstream consumption."""
        return asdict(self)


# ── Private helpers — access resolution ───────────────────────────────────────

def _resolve_allowed_equipment(available: list[str]) -> tuple[list[str], bool]:
    """
    Filters the raw available_equipment_types list to known valid values
    and handles the empty-input edge case.

    Returns
    -------
    (allowed, no_equipment_fallback)
        allowed               : ordered list of valid equipment type strings
        no_equipment_fallback : True if the input was empty and we defaulted
                                to [_FALLBACK_EQUIPMENT]

    Notes
    -----
    In production, the serializer guarantees:
        1. available_equipment_types is non-empty (min_length=1)
        2. every element is one of the three known values

    This function still defends against both conditions because this module
    may be called directly in tests or future integrations that bypass the
    serializer.  Unknown type strings are silently dropped; if the result is
    empty we fall back to bodyweight.
    """
    # Filter to known types only; preserve the serializer's sorted order.
    filtered = [t for t in available if t in KNOWN_EQUIPMENT_TYPES]

    if filtered:
        return filtered, False

    # Empty result — apply the bodyweight fallback.
    return [_FALLBACK_EQUIPMENT], True


def _resolve_preference(
    preferred:    list[str],
    allowed_set:  set[str],
) -> tuple[list[str], list[str]]:
    """
    Splits the raw preferred_equipment_types list into:
        effective   — preferences that are actually in allowed_equipment
        unavailable — preferences that were stated but are not available

    The serializer enforces preferred ⊆ available, so in production
    `unavailable` will always be empty.  This function captures the split
    for defensive safety and unit-test support.

    Returns
    -------
    (effective_preferred, unavailable_preference)
        Both lists contain only valid equipment type strings.
        Both are sorted for stable, consistent output.
    """
    effective   = sorted(t for t in preferred if t in allowed_set)
    unavailable = sorted(t for t in preferred if t not in allowed_set)
    return effective, unavailable


# ── Private helpers — selection bias ─────────────────────────────────────────

def _compute_selection_bias(
    allowed:              list[str],
    effective_preferred:  list[str],
) -> dict[str, float]:
    """
    Computes a {equipment_type: float} selection bias dict.
    All values sum to 1.0 (within floating-point rounding).

    The bias is derived from the _PREFERENCE_ALLOCATION table keyed by
    (n_allowed_total, n_effective_preferred).

    When no preference exists or all types are equally preferred, weights
    are distributed equally.

    When a preference exists, preferred types receive a higher share.
    The remaining share is divided equally among non-preferred types,
    ensuring they remain selectable (bias ≠ exclusion).

    Parameters
    ----------
    allowed             : ordered list of all accessible equipment types
    effective_preferred : subset of allowed that the user prefers
    """
    n_allowed    = len(allowed)
    n_preferred  = len(effective_preferred)
    preferred_set = set(effective_preferred)

    # ── Edge: nothing allowed (should not happen after _resolve_allowed_equipment)
    if n_allowed == 0:
        return {}

    # ── No discriminating preference signal → equal weights
    if n_preferred == 0 or n_preferred == n_allowed:
        equal = round(1.0 / n_allowed, 4)
        return {t: equal for t in allowed}

    # ── Preference signal exists — look up the weight allocation
    pref_share, non_pref_share = _PREFERENCE_ALLOCATION[(n_allowed, n_preferred)]

    n_non_preferred   = n_allowed - n_preferred
    pref_weight_each  = round(pref_share  / n_preferred,   4)
    non_pref_each     = round(non_pref_share / n_non_preferred, 4) if n_non_preferred else 0.0

    return {
        t: (pref_weight_each if t in preferred_set else non_pref_each)
        for t in allowed
    }


# ── Private helpers — hard constraints ────────────────────────────────────────

def _build_hard_constraints(allowed: list[str]) -> dict[str, bool]:
    """
    Produces a flat dict of boolean constraint flags for downstream modules.

    All flags describe access-level restrictions — what the system is NOT
    allowed to do — regardless of preference.

    exclude_unavailable_equipment
        Always True.  The foundational rule: never assign an exercise
        that requires equipment the user does not have access to.

    single_modality_only
        True when only one equipment type is available.  The exercise
        selection layer must draw ALL exercises from that single modality.

    machines_excluded / free_weights_excluded / bodyweight_excluded
        True when the corresponding type is absent from allowed_equipment.
        These are convenience flags so downstream modules do not need to
        check set membership on the allowed list repeatedly.
    """
    allowed_set = set(allowed)
    return {
        "exclude_unavailable_equipment": True,          # always enforced
        "single_modality_only":          len(allowed) == 1,
        "machines_excluded":             "machines"     not in allowed_set,
        "free_weights_excluded":         "free_weights" not in allowed_set,
        "bodyweight_excluded":           "bodyweight"   not in allowed_set,
    }


# ── Private helpers — equipment access map ────────────────────────────────────

def _build_access_map(allowed: list[str]) -> dict[str, bool]:
    """
    Returns a {equipment_type: bool} dict for all known types.
    Missing types are explicitly False, present types are True.

    Downstream modules can do fast conditional checks without set operations:
        if access_map["machines"]: ...
    """
    return {t: (t in allowed) for t in sorted(KNOWN_EQUIPMENT_TYPES)}


# ── Private helpers — flags and notes ─────────────────────────────────────────

def _build_caution_flags(
    no_equipment_fallback:  bool,
    unavailable_preference: list[str],
    fallback_triggered:     bool,
    allowed:                list[str],
) -> list[str]:
    """
    Emits machine-readable caution flags for downstream modules to check.

    Flags are short, namespaced strings that describe conditions requiring
    attention — they do not prevent operation, but signal that the system
    made an adjustment the AI prompt builder should explain to the user.
    """
    flags: list[str] = []

    if no_equipment_fallback:
        # No equipment was specified — we defaulted to bodyweight.
        # This warrants explicit notification in the AI prompt.
        flags.append("no_equipment_specified_bodyweight_fallback")

    if unavailable_preference:
        # User asked for equipment they don't have access to.
        # The serializer prevents this in production, so this flag primarily
        # surfaces in testing — but it is important to capture for future-proofing.
        for t in unavailable_preference:
            flags.append(f"preferred_equipment_unavailable:{t}")

    if fallback_triggered:
        # Preference was set but none of the preferred types were available.
        # Exercise selection should proceed without any preference bias.
        flags.append("preference_fallback_applied_no_bias")

    if len(allowed) == 1:
        # Only one modality — exercise variety will be limited.
        flags.append(f"single_modality_constraint:{allowed[0]}")

    return flags


def _build_planning_notes(
    allowed:                list[str],
    effective_preferred:    list[str],
    unavailable_preference: list[str],
    fallback_triggered:     bool,
    no_equipment_fallback:  bool,
    selection_bias:         dict[str, float],
    hard_constraints:       dict[str, bool],
) -> list[str]:
    """
    Generates human-readable planning notes explaining the equipment constraint
    decisions made by this module.

    These notes are included in the OpenAI prompt so the model understands
    the equipment context it must respect.
    """
    notes: list[str] = []

    # ── Access note ────────────────────────────────────────────────────────
    if no_equipment_fallback:
        notes.append(
            "No equipment access data was provided. "
            f"Defaulting to '{_FALLBACK_EQUIPMENT}' only — all exercises must use bodyweight."
        )
    else:
        allowed_str = ", ".join(allowed)
        notes.append(
            f"Available equipment: {allowed_str}. "
            "Exercise selection is hard-limited to these types. "
            "No exercises requiring other equipment may be programmed."
        )

    # ── Preference note ────────────────────────────────────────────────────
    if not effective_preferred and not unavailable_preference:
        notes.append(
            "No equipment preference stated. "
            "Selection bias is distributed equally across all available types."
        )
    elif effective_preferred:
        pref_str = ", ".join(effective_preferred)
        bias_str = ", ".join(
            f"{t}: {w:.0%}" for t, w in selection_bias.items()
        )
        notes.append(
            f"Preferred equipment: {pref_str}. "
            f"Selection bias applied — {bias_str}. "
            "Non-preferred types remain available but will be used less frequently."
        )

    # ── Unavailable preference note ────────────────────────────────────────
    if unavailable_preference:
        unavail_str = ", ".join(unavailable_preference)
        notes.append(
            f"Requested preferred equipment not available: {unavail_str}. "
            "These preferences have been dropped. "
            + (
                "Exercise selection proceeds without a preference bias."
                if fallback_triggered
                else "Remaining preferences are still active."
            )
        )

    # ── Single modality note ───────────────────────────────────────────────
    if hard_constraints.get("single_modality_only"):
        notes.append(
            f"Only one equipment type available: '{allowed[0]}'. "
            "All exercises must be drawn from this single modality. "
            "Exercise variety may be limited — the AI should maximise "
            "movement pattern diversity within this constraint."
        )

    # ── Specific exclusion notes ───────────────────────────────────────────
    if hard_constraints.get("free_weights_excluded"):
        notes.append(
            "Free weights are not available. "
            "Barbell and dumbbell exercises must not be programmed."
        )
    if hard_constraints.get("machines_excluded"):
        notes.append(
            "Machines are not available. "
            "Cable, selectorized, and plate-loaded machine exercises must not be programmed."
        )
    if hard_constraints.get("bodyweight_excluded"):
        notes.append(
            "Bodyweight is not listed as an available equipment type. "
            "Programmed bodyweight sessions should be avoided, though minimal "
            "unloaded warmup movements (mobility, activation) may still be used."
        )

    return notes


# ── Public API ────────────────────────────────────────────────────────────────

def apply_equipment_rules(profile: dict) -> EquipmentConstraintProfile:
    """
    Converts the user's equipment access and preference data into a
    deterministic EquipmentConstraintProfile.

    Parameters
    ----------
    profile : dict
        A UserWorkoutProfile dict (from UserWorkoutProfile.to_dict()) or any
        dict containing at minimum:

            available_equipment_types : list[str]
                Equipment types the user has physical access to.
                Expected values: "machines", "free_weights", "bodyweight".
                In production, validated non-empty by the serializer.

            preferred_equipment_types : list[str]
                Equipment types the user prefers to use.
                In production, validated as a subset of available_equipment_types
                by the serializer.  May be empty (no stated preference).

    Returns
    -------
    EquipmentConstraintProfile
        A deterministic constraint document for downstream modules.

    Raises
    ------
    No exceptions are raised.  All edge cases (empty input, unknown types,
    unavailable preferences) are handled defensively with fallbacks and flags.

    Examples
    --------
    # User has all three types, prefers free weights
    profile = {
        "available_equipment_types": ["machines", "free_weights", "bodyweight"],
        "preferred_equipment_types": ["free_weights"],
    }
    result = apply_equipment_rules(profile)
    # result.allowed_equipment          → ["machines", "free_weights", "bodyweight"]
    # result.effective_preferred_equipment → ["free_weights"]
    # result.selection_bias             → {"bodyweight": 0.2, "free_weights": 0.6, "machines": 0.2}
    # result.hard_constraints["single_modality_only"] → False

    # User has only machines, no preference
    profile = {
        "available_equipment_types": ["machines"],
        "preferred_equipment_types": [],
    }
    result = apply_equipment_rules(profile)
    # result.allowed_equipment          → ["machines"]
    # result.selection_bias             → {"machines": 1.0}
    # result.hard_constraints["single_modality_only"] → True
    # result.hard_constraints["free_weights_excluded"] → True
    """
    # ── Extract raw inputs ────────────────────────────────────────────────────
    raw_available  = list(profile.get("available_equipment_types", []))
    raw_preferred  = list(profile.get("preferred_equipment_types", []))

    # ── Resolve allowed equipment ─────────────────────────────────────────────
    # Filters to known types and applies the bodyweight fallback if empty.
    allowed, no_equipment_fallback = _resolve_allowed_equipment(raw_available)
    allowed_set = set(allowed)

    # ── Resolve preference ────────────────────────────────────────────────────
    # Splits stated preferences into those that are available and those that are not.
    effective_preferred, unavailable_preference = _resolve_preference(
        raw_preferred, allowed_set
    )

    # Preference is satisfied when every stated preference is available.
    preference_satisfied = len(unavailable_preference) == 0

    # Fallback is triggered when preferences were stated but NONE are available.
    # In this case, selection_bias reverts to equal weighting (no bias applied).
    fallback_triggered = bool(raw_preferred) and len(effective_preferred) == 0

    # ── Selection bias ────────────────────────────────────────────────────────
    # Compute numeric float weights per equipment type.
    # Uses effective_preferred (not raw_preferred) so unavailable types
    # never influence the bias calculation.
    selection_bias = _compute_selection_bias(allowed, effective_preferred)

    # ── Hard constraints ──────────────────────────────────────────────────────
    hard_constraints = _build_hard_constraints(allowed)

    # ── Equipment access map ──────────────────────────────────────────────────
    access_map = _build_access_map(allowed)

    # ── Caution flags ─────────────────────────────────────────────────────────
    caution_flags = _build_caution_flags(
        no_equipment_fallback  = no_equipment_fallback,
        unavailable_preference = unavailable_preference,
        fallback_triggered     = fallback_triggered,
        allowed                = allowed,
    )

    # ── Planning notes ────────────────────────────────────────────────────────
    notes = _build_planning_notes(
        allowed                = allowed,
        effective_preferred    = effective_preferred,
        unavailable_preference = unavailable_preference,
        fallback_triggered     = fallback_triggered,
        no_equipment_fallback  = no_equipment_fallback,
        selection_bias         = selection_bias,
        hard_constraints       = hard_constraints,
    )

    return EquipmentConstraintProfile(
        # Access
        allowed_equipment         = allowed,
        equipment_access_map      = access_map,

        # Preference
        requested_preferred_equipment = sorted(set(raw_preferred)),
        effective_preferred_equipment = effective_preferred,
        unavailable_preference        = unavailable_preference,
        preference_satisfied          = preference_satisfied,
        fallback_triggered            = fallback_triggered,
        no_equipment_fallback         = no_equipment_fallback,

        # Selection bias
        selection_bias            = selection_bias,

        # Hard constraints
        hard_constraints          = hard_constraints,

        # Meta
        caution_flags             = caution_flags,
        planning_notes            = notes,
    )
