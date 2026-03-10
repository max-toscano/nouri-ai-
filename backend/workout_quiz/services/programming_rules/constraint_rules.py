# ──────────────────────────────────────────────────────────────────────────────
# services/programming_rules/constraint_rules.py  —  workout_quiz
#
# PURPOSE
# -------
# Third module of the programming rules engine.
#
# Accepts a normalized UserWorkoutProfile (or equivalent dict) and derives:
#   - which movements are hard-excluded from the program
#   - which movements require caution and potential regression logic
#   - restriction severity levels for lower body, upper body, spine, and impact
#   - an overall programming caution level
#   - which equipment modalities are allowed / discouraged
#   - how strongly preferred equipment should bias exercise selection
#   - structural constraints the split-construction layer must respect
#   - human-readable planning notes explaining each decision
#
# PIPELINE POSITION
# -----------------
# UserWorkoutProfile
#     → apply_goal_rules()              (goal_rules.py)
#         → GoalProgrammingProfile
#     → apply_split_volume_rules()      (split_volume_rules.py)
#         → SplitVolumeRulesProfile
#     → apply_constraint_rules()        ← THIS FILE
#         → ConstraintRulesProfile
#             → WorkoutProgrammingContext  (future — assembles all rule profiles)
#                 → OpenAI prompt builder  (future)
#
# IMPORTANT: this module does NOT generate exercises or workout sessions.
# It produces a constraint document that all downstream modules must honour.
# The split-construction and exercise-selection layers read this profile
# before making any exercise or structure decisions.
#
# DESIGN PRINCIPLES
# -----------------
# - Deterministic: same input always produces the same output.
# - No side effects: pure function, no DB or API calls.
# - Lookup tables drive injury logic — adding a new body area or movement
#   means editing a table, not adding branches throughout the function.
# - Conservative by default: when in doubt, caution_movements > nothing.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Restriction severity helpers ──────────────────────────────────────────────

# Severity is ordered so we can take the maximum across multiple injury areas.
_SEVERITY_RANK: dict[str, int] = {
    "none":     0,
    "low":      1,
    "moderate": 2,
    "high":     3,
}
_RANK_TO_SEVERITY: dict[int, str] = {v: k for k, v in _SEVERITY_RANK.items()}


def _max_severity(*levels: str) -> str:
    """Returns the highest severity string from the supplied levels."""
    return _RANK_TO_SEVERITY[max(_SEVERITY_RANK[lv] for lv in levels)]


# ── Output field value constants ──────────────────────────────────────────────

class RestrictionLevel:
    NONE     = "none"
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


class ExerciseModality:
    MACHINE_BASED    = "machine_based"
    FREE_WEIGHT_BASED = "free_weight_based"
    BODYWEIGHT_BASED  = "bodyweight_based"


class EquipmentBias:
    """
    How strongly preferred_equipment_types should skew exercise selection
    away from the other available types.

    none     → preferred == available; no bias needed
    low      → slight preference, but other types used freely
    moderate → preferred types used by default; others as supplement
    high     → preferred types dominate; others only when preferred option absent
    """
    NONE     = "none"
    LOW      = "low"
    MODERATE = "moderate"
    HIGH     = "high"


# ── Injury lookup tables ──────────────────────────────────────────────────────
# These tables are the single source of truth for how injured body areas map
# to restriction levels and implied caution movements.
#
# Each entry maps an injured_area value to a severity string.
# Areas not listed in a table contribute no restriction to that dimension.

# Lower body restriction: how much each injured area limits lower body training.
_LOWER_BODY_RESTRICTION: dict[str, str] = {
    "knees":  RestrictionLevel.HIGH,
    "hips":   RestrictionLevel.MODERATE,
    "ankles": RestrictionLevel.MODERATE,
}

# Upper body restriction: how much each area limits upper body training.
_UPPER_BODY_RESTRICTION: dict[str, str] = {
    "shoulders": RestrictionLevel.HIGH,
    "elbows":    RestrictionLevel.MODERATE,
    "wrists":    RestrictionLevel.MODERATE,
    "neck":      RestrictionLevel.LOW,
}

# Spine loading caution: how much each area demands reduced spinal stress.
_SPINE_LOADING_CAUTION: dict[str, str] = {
    "lower_back": RestrictionLevel.HIGH,
    "upper_back": RestrictionLevel.MODERATE,
    "neck":       RestrictionLevel.MODERATE,
}

# Impact caution: how much each area demands low-impact programming.
_IMPACT_CAUTION: dict[str, str] = {
    "knees":  RestrictionLevel.HIGH,
    "ankles": RestrictionLevel.HIGH,
    "hips":   RestrictionLevel.MODERATE,
}

# Implied caution movements per injured area.
# These are movements that should be treated carefully when an area is injured,
# EVEN IF the user did not explicitly list them in movements_to_avoid.
# They become caution_movements (not excluded_movements) — they are still
# allowed but must use conservative loading, regression, or supported variants.
_AREA_IMPLIED_CAUTION_MOVEMENTS: dict[str, list[str]] = {
    "knees":      ["lunging", "running", "squatting"],
    "hips":       ["squatting", "lunging"],
    "ankles":     ["running", "jumping"],
    "lower_back": ["bending", "squatting"],
    "upper_back": ["pulling", "bending"],
    "shoulders":  ["overhead_pressing", "pushing", "pulling"],
    "elbows":     ["pushing", "pulling"],
    "wrists":     ["pushing", "pulling"],
    "neck":       ["overhead_pressing"],
}

# Split-level structural constraint flags emitted when a restriction threshold
# is reached.  The split-construction layer reads these to enforce safe session
# structures (e.g. not placing high spine-load exercises on every training day).
_RESTRICTION_STRUCTURAL_FLAGS: dict[str, dict[str, str]] = {
    # key: (restriction_field, threshold_level) → flag string
    # stored as a flat list of (condition_fn, flag) pairs — see _build_split_constraints
}


# ── Equipment lookup table ─────────────────────────────────────────────────────

# Maps equipment_type strings to their corresponding exercise modality label.
_EQUIPMENT_TO_MODALITY: dict[str, str] = {
    "machines":    ExerciseModality.MACHINE_BASED,
    "free_weights": ExerciseModality.FREE_WEIGHT_BASED,
    "bodyweight":  ExerciseModality.BODYWEIGHT_BASED,
}


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class ConstraintRulesProfile:
    """
    Output of the injury and equipment constraint rules engine.

    This is a constraint document — not a workout.  Every downstream module
    (split construction, exercise selection, volume distribution) must check
    this profile before making a programming decision.

    Injury fields
    -------------
    has_injuries
        Pass-through flag.  When False, all restriction levels are 'none'
        and excluded/caution lists are empty.

    injured_areas
        Pass-through list of affected body areas.

    injury_notes
        Pass-through free-text from the user, forwarded to the AI prompt
        so the model understands the qualitative context.

    Movement constraint fields
    --------------------------
    excluded_movements
        Movements the user explicitly listed in movements_to_avoid.
        These are hard blocks — later modules must not program them.

    caution_movements
        Movements implied by injured areas that are NOT hard-excluded.
        Later modules may include these only with conservative loading,
        supported/regressed exercise variants, and reduced frequency.

    Restriction level fields
    ------------------------
    lower_body_restriction_level
        How much lower body training capacity is limited.  none|low|moderate|high.

    upper_body_restriction_level
        How much upper body training capacity is limited.  none|low|moderate|high.

    spine_loading_caution
        How carefully spinal-loading movements must be managed.  none|low|moderate|high.

    impact_caution
        How carefully impact-based movements (jumping, running) must be managed.
        none|low|moderate|high.

    programming_caution_level
        Overall severity of injury constraints.  Derived as the maximum of all
        restriction levels above.  Later modules use this as a quick global check
        before reading the more granular fields.

    Equipment fields
    ----------------
    available_equipment_types
        Pass-through from UserWorkoutProfile.  Determines which modalities
        the exercise-selection layer is allowed to draw from.

    preferred_equipment_types
        Pass-through from UserWorkoutProfile.  Provides the bias signal.

    equipment_selection_bias
        How strongly preferred_equipment_types should skew exercise selection.
        none | low | moderate | high.
        Computed from the gap between available and preferred lists.

    allowed_exercise_modalities
        Modality strings derived directly from available_equipment_types.
        Exercise selection must stay within this list.

    discouraged_exercise_modalities
        Modality strings for equipment types that are available but NOT preferred.
        Exercise selection may still use these, but should deprioritize them.

    Structural constraint fields
    ----------------------------
    split_structure_constraints
        List of short rule flag strings the split-construction layer must enforce.
        Examples:
            "avoid_high_spine_loading_days"
            "avoid_lower_body_dominant_frequency"
            "avoid_lower_body_impact_work"
            "avoid_heavy_upper_body_pressing"
            "prefer_stable_exercise_variations"
            "prefer_machine_or_supported_variations"

    planning_notes
        Human-readable explanations of the key constraint decisions.
        Included in the OpenAI prompt so the model has explicit context
        for the restrictions it must respect.
    """

    # Injury
    has_injuries:   bool
    injured_areas:  list
    injury_notes:   Optional[str]

    # Movement constraints
    excluded_movements: list
    caution_movements:  list

    # Restriction levels
    lower_body_restriction_level: str
    upper_body_restriction_level: str
    spine_loading_caution:        str
    impact_caution:               str
    programming_caution_level:    str

    # Equipment
    available_equipment_types:    list
    preferred_equipment_types:    list
    equipment_selection_bias:     str
    allowed_exercise_modalities:  list
    discouraged_exercise_modalities: list

    # Structural constraints
    split_structure_constraints:  list
    planning_notes:               list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Returns a plain dict for JSON serialization or downstream consumption."""
        return asdict(self)


# ── Private helpers — injury logic ────────────────────────────────────────────

def _compute_restriction_level(
    injured_areas: list[str],
    restriction_table: dict[str, str],
) -> str:
    """
    Scans the injured areas list against a restriction table and returns the
    maximum severity found.  Returns 'none' if no relevant areas are injured.
    """
    levels = [
        restriction_table[area]
        for area in injured_areas
        if area in restriction_table
    ]
    if not levels:
        return RestrictionLevel.NONE
    return _max_severity(*levels)


def _derive_caution_movements(
    injured_areas: list[str],
    excluded_movements: set[str],
) -> list[str]:
    """
    Builds the caution_movements list from injury-implied movement sensitivities.

    A movement becomes a caution movement when:
    1. An injured area implies it should be treated carefully, AND
    2. The user has NOT already hard-excluded it via movements_to_avoid.

    This keeps excluded_movements and caution_movements strictly disjoint.
    """
    implied: set[str] = set()
    for area in injured_areas:
        for movement in _AREA_IMPLIED_CAUTION_MOVEMENTS.get(area, []):
            if movement not in excluded_movements:
                implied.add(movement)
    return sorted(implied)


def _build_split_structure_constraints(
    lower_body:   str,
    upper_body:   str,
    spine:        str,
    impact:       str,
    has_injuries: bool,
    equipment_bias: str,
) -> list[str]:
    """
    Returns a deterministic list of structural constraint flag strings.

    These flags are consumed by the split-construction layer to enforce
    safe session structures.  Each flag is a short, understandable directive.
    """
    flags: list[str] = []

    if spine in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        flags.append("avoid_high_spine_loading_days")

    if lower_body in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        flags.append("avoid_lower_body_dominant_frequency")

    if impact in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        flags.append("avoid_lower_body_impact_work")

    if upper_body in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        flags.append("avoid_heavy_upper_body_pressing")

    # Any meaningful injury warrants more stable / supported exercise choices.
    if has_injuries and any(
        lv in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH)
        for lv in [lower_body, upper_body, spine, impact]
    ):
        flags.append("prefer_stable_exercise_variations")

    # If equipment bias toward preferred types is active AND there are injuries,
    # further flag that machine or supported variants should be preferred —
    # machines provide more stability and safer load paths than free weights
    # when injuries are present.
    if has_injuries and equipment_bias in (EquipmentBias.MODERATE, EquipmentBias.HIGH):
        flags.append("prefer_machine_or_supported_variations")

    return flags


# ── Private helpers — equipment logic ─────────────────────────────────────────

def _compute_equipment_bias(
    available: list[str],
    preferred: list[str],
) -> str:
    """
    Computes how strongly preferred_equipment_types should bias exercise selection.

    Logic
    -----
    If preferred == available (no non-preferred options exist), there is nothing
    to bias toward — return 'none'.

    Otherwise, count how many available types are NOT in preferred.  The more
    non-preferred options that exist, the stronger the bias signal needed to
    steer selection toward the preferred types:
        0 non-preferred → none
        1 non-preferred → moderate
        2+ non-preferred → high
    """
    available_set = set(available)
    preferred_set = set(preferred)
    non_preferred_count = len(available_set - preferred_set)

    if non_preferred_count == 0:
        return EquipmentBias.NONE
    if non_preferred_count == 1:
        return EquipmentBias.MODERATE
    return EquipmentBias.HIGH


def _build_exercise_modalities(
    available: list[str],
    preferred: list[str],
) -> tuple[list[str], list[str]]:
    """
    Returns (allowed_modalities, discouraged_modalities).

    allowed      → every modality corresponding to an available equipment type
    discouraged  → modalities that are available but NOT in preferred
                   (they remain usable but should not be the default choice)
    """
    preferred_set = set(preferred)
    allowed: list[str]      = []
    discouraged: list[str]  = []

    for equipment_type in available:
        modality = _EQUIPMENT_TO_MODALITY.get(equipment_type)
        if modality is None:
            continue
        allowed.append(modality)
        if equipment_type not in preferred_set:
            discouraged.append(modality)

    return sorted(allowed), sorted(discouraged)


# ── Private helpers — planning notes ──────────────────────────────────────────

def _build_planning_notes(
    has_injuries:    bool,
    injured_areas:   list[str],
    excluded:        list[str],
    caution:         list[str],
    lower_body:      str,
    upper_body:      str,
    spine:           str,
    impact:          str,
    caution_level:   str,
    available_equip: list[str],
    preferred_equip: list[str],
    equip_bias:      str,
) -> list[str]:
    """Generates concise, human-readable notes explaining the constraint decisions."""
    notes: list[str] = []

    # ── Injury note ───────────────────────────────────────────────────────────
    if not has_injuries:
        notes.append(
            "No injuries reported. No movement restrictions or caution flags applied."
        )
    else:
        areas_str = ", ".join(injured_areas) if injured_areas else "unspecified areas"
        notes.append(
            f"User reported injuries affecting: {areas_str}. "
            f"Overall programming caution level: {caution_level}."
        )

    # ── Excluded movements note ───────────────────────────────────────────────
    if excluded:
        notes.append(
            f"Hard-excluded movements (never program): {', '.join(excluded)}."
        )

    # ── Caution movements note ────────────────────────────────────────────────
    if caution:
        notes.append(
            f"Caution movements (use only with conservative loading and stable variants): "
            f"{', '.join(caution)}."
        )

    # ── Restriction level notes ───────────────────────────────────────────────
    if lower_body in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        notes.append(
            f"Lower body restriction level is '{lower_body}'. "
            "Reduce lower body dominant session frequency and avoid high knee-stress movements."
        )
    if upper_body in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        notes.append(
            f"Upper body restriction level is '{upper_body}'. "
            "Avoid heavy overhead and pressing movements. Use supported or neutral-grip alternatives."
        )
    if spine in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        notes.append(
            f"Spine loading caution level is '{spine}'. "
            "Limit axially-loaded movements. Prefer horizontal or unloaded spinal positions."
        )
    if impact in (RestrictionLevel.MODERATE, RestrictionLevel.HIGH):
        notes.append(
            f"Impact caution level is '{impact}'. "
            "Exclude or minimise plyometrics, running, and jump-based conditioning."
        )

    # ── Equipment note ────────────────────────────────────────────────────────
    avail_str = ", ".join(available_equip) if available_equip else "none"
    pref_str  = ", ".join(preferred_equip) if preferred_equip else "none"
    notes.append(
        f"Available equipment: {avail_str}. "
        f"Preferred equipment: {pref_str}. "
        f"Equipment selection bias: {equip_bias}."
    )

    return notes


# ── Public API ────────────────────────────────────────────────────────────────

def apply_constraint_rules(profile: dict) -> ConstraintRulesProfile:
    """
    Derives injury and equipment constraint rules from the normalized workout profile.

    Parameters
    ----------
    profile : dict
        A UserWorkoutProfile dict (from UserWorkoutProfile.to_dict()) or any
        dict containing at minimum:
            has_injuries
            injured_areas
            movements_to_avoid
            injury_notes
            available_equipment_types
            preferred_equipment_types

    Returns
    -------
    ConstraintRulesProfile
        A constraint document that all downstream modules must respect.
    """
    # ── Extract inputs ────────────────────────────────────────────────────────
    has_injuries      = bool(profile.get("has_injuries", False))
    injured_areas     = list(profile.get("injured_areas", []))
    movements_to_avoid = list(profile.get("movements_to_avoid", []))
    injury_notes      = profile.get("injury_notes") or None
    available_equip   = list(profile.get("available_equipment_types", []))
    preferred_equip   = list(profile.get("preferred_equipment_types", []))

    # ── Movement constraints ──────────────────────────────────────────────────
    # User-stated avoidances become hard exclusions.
    excluded_movements = sorted(set(movements_to_avoid))

    if has_injuries:
        caution_movements = _derive_caution_movements(
            injured_areas,
            set(excluded_movements),
        )
    else:
        caution_movements = []

    # ── Restriction levels ────────────────────────────────────────────────────
    if has_injuries:
        lower_body_restriction = _compute_restriction_level(
            injured_areas, _LOWER_BODY_RESTRICTION
        )
        upper_body_restriction = _compute_restriction_level(
            injured_areas, _UPPER_BODY_RESTRICTION
        )
        spine_caution = _compute_restriction_level(
            injured_areas, _SPINE_LOADING_CAUTION
        )
        impact_caution = _compute_restriction_level(
            injured_areas, _IMPACT_CAUTION
        )
    else:
        lower_body_restriction = RestrictionLevel.NONE
        upper_body_restriction = RestrictionLevel.NONE
        spine_caution          = RestrictionLevel.NONE
        impact_caution         = RestrictionLevel.NONE

    # ── Overall caution level ─────────────────────────────────────────────────
    if not has_injuries:
        caution_level = RestrictionLevel.NONE
    else:
        caution_level = _max_severity(
            lower_body_restriction,
            upper_body_restriction,
            spine_caution,
            impact_caution,
        )
        # Ensure at least "low" when there ARE injuries, even if the specific
        # areas don't map to a known restriction (e.g. forearms, neck alone).
        if caution_level == RestrictionLevel.NONE:
            caution_level = RestrictionLevel.LOW

    # ── Equipment ─────────────────────────────────────────────────────────────
    equip_bias = _compute_equipment_bias(available_equip, preferred_equip)
    allowed_modalities, discouraged_modalities = _build_exercise_modalities(
        available_equip, preferred_equip
    )

    # ── Split structural constraints ──────────────────────────────────────────
    split_constraints = _build_split_structure_constraints(
        lower_body    = lower_body_restriction,
        upper_body    = upper_body_restriction,
        spine         = spine_caution,
        impact        = impact_caution,
        has_injuries  = has_injuries,
        equipment_bias = equip_bias,
    )

    # ── Planning notes ────────────────────────────────────────────────────────
    notes = _build_planning_notes(
        has_injuries    = has_injuries,
        injured_areas   = injured_areas,
        excluded        = excluded_movements,
        caution         = caution_movements,
        lower_body      = lower_body_restriction,
        upper_body      = upper_body_restriction,
        spine           = spine_caution,
        impact          = impact_caution,
        caution_level   = caution_level,
        available_equip = available_equip,
        preferred_equip = preferred_equip,
        equip_bias      = equip_bias,
    )

    return ConstraintRulesProfile(
        # Injury
        has_injuries  = has_injuries,
        injured_areas = injured_areas,
        injury_notes  = injury_notes,

        # Movement constraints
        excluded_movements = excluded_movements,
        caution_movements  = caution_movements,

        # Restriction levels
        lower_body_restriction_level = lower_body_restriction,
        upper_body_restriction_level = upper_body_restriction,
        spine_loading_caution        = spine_caution,
        impact_caution               = impact_caution,
        programming_caution_level    = caution_level,

        # Equipment
        available_equipment_types       = available_equip,
        preferred_equipment_types       = preferred_equip,
        equipment_selection_bias        = equip_bias,
        allowed_exercise_modalities     = allowed_modalities,
        discouraged_exercise_modalities = discouraged_modalities,

        # Structural constraints
        split_structure_constraints = split_constraints,
        planning_notes              = notes,
    )
