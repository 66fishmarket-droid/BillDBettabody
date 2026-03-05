"""
Bill D'Bettabody - Weight Recommendation Engine

Calculates recommended_load_kg for session steps based on Exercise Bests.
Called at session load time to enrich steps before they reach the frontend.

Sources (in priority order):
  prescribed       → Bill already set load_kg in the step
  e1rm_calculated  → Derived from client's e1RM for this exact exercise
  inferred         → Derived from a related exercise via INFERENCE_MAP
  no_data          → Insufficient data; no recommendation made
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cross-exercise inference map
# Format: target_exercise → (source_exercise, ratio)
# ratio × source_e1rm ≈ estimated_e1rm for target_exercise
# ---------------------------------------------------------------------------
INFERENCE_MAP = {
    # Lower body
    "Front Squat":               ("Barbell Back Squat",     0.85),
    "Goblet Squat":              ("Barbell Back Squat",     0.65),
    "Leg Press":                 ("Barbell Back Squat",     1.75),
    "Romanian Deadlift":         ("Deadlift",               0.75),
    "Trap Bar Deadlift":         ("Deadlift",               0.97),
    "Bulgarian Split Squat":     ("Barbell Back Squat",     0.50),
    # Upper push
    "Dumbbell Bench Press":      ("Barbell Bench Press",    0.85),
    "Incline Barbell Press":     ("Barbell Bench Press",    0.85),
    "Dumbbell Shoulder Press":   ("Barbell Overhead Press", 0.85),
    "Push Press":                ("Barbell Overhead Press", 1.15),
    # Upper pull
    "Dumbbell Row":              ("Barbell Bent-Over Row",  0.70),
    "Cable Row":                 ("Barbell Bent-Over Row",  0.85),
    "Lat Pulldown":              ("Pull-Up",                1.25),
    "Assisted Pull-Up Machine":  ("Pull-Up",                0.85),
}

_NO_DATA = {
    'recommended_load_kg': None,
    'recommendation_source': 'no_data',
    'recommendation_note': 'No recommendation — set your own weight',
}


def enrich_steps_with_recommendations(steps, exercise_bests, client_profile):
    """
    In-place enrich each step with recommended_load_kg, recommendation_source,
    and recommendation_note.

    Args:
        steps:           list of step dicts (modified in place)
        exercise_bests:  list of Exercise_Bests dicts (from get_session_detail)
        client_profile:  dict with training_experience etc. (may be {})
    """
    bests_lookup = {}
    for b in (exercise_bests or []):
        name = str(b.get('exercise_name', '') or '').strip().lower()
        if name:
            bests_lookup[name] = b

    profile = client_profile or {}
    for step in steps:
        try:
            rec = recommend_load(step, bests_lookup, profile)
            step.update(rec)
        except Exception as e:
            logger.warning(
                "[WeightRecommender] Error on step '%s': %s",
                step.get('exercise_name', '?'), e
            )
            step.update(_NO_DATA)


def recommend_load(step, bests_lookup, client_profile):
    """
    Calculate recommended load for a single step.

    Args:
        step:           dict — step data (with Exercise_Library fields joined)
        bests_lookup:   dict keyed by exercise_name.lower()
        client_profile: dict — client profile

    Returns:
        dict with keys: recommended_load_kg, recommendation_source,
                        recommendation_note
    """
    # Only applies to main-segment steps
    if str(step.get('segment_type', '') or '').lower() != 'main':
        return _NO_DATA

    exercise_name = str(step.get('exercise_name', '') or '').strip()
    if not exercise_name:
        return _NO_DATA

    # Skip non-strength steps
    step_type = str(step.get('step_type', '') or '').lower()
    metric_family = str(step.get('metric_family_default', '') or '').lower()
    if metric_family and metric_family not in ('strength', ''):
        return _NO_DATA
    if step_type in ('mobility', 'activation', 'pulse_raise', 'cardio',
                     'steady_state', 'intervals'):
        return _NO_DATA

    # ── Step 1: Prescribed load takes precedence ─────────────────────────────
    load_kg = _parse_float(step.get('load_kg')) or _parse_float(step.get('load_start_kg'))
    if load_kg and load_kg > 0:
        return {
            'recommended_load_kg': _round_to_increment(
                load_kg, _increment_for(exercise_name)
            ),
            'recommendation_source': 'prescribed',
            'recommendation_note': "Bill's prescription",
        }

    target_reps = _parse_target_reps(step)
    target_rpe = _parse_target_rpe(step) or 7.0
    if not target_reps or target_reps <= 0:
        return _NO_DATA

    increment = _increment_for(exercise_name)
    is_beginner = _is_beginner(client_profile)

    # ── Step 2: Direct e1RM lookup ───────────────────────────────────────────
    best = bests_lookup.get(exercise_name.lower())
    if best:
        e1rm = _get_e1rm(best)
        if e1rm and e1rm > 0:
            load = _load_from_e1rm(e1rm, target_reps, target_rpe)
            if is_beginner:
                load *= 0.90
            return {
                'recommended_load_kg': _round_to_increment(load, increment),
                'recommendation_source': 'e1rm_calculated',
                'recommendation_note': f"Based on your {exercise_name} data",
            }

    # ── Step 3: Cross-exercise inference ─────────────────────────────────────
    if exercise_name in INFERENCE_MAP:
        source_name, ratio = INFERENCE_MAP[exercise_name]
        source_best = bests_lookup.get(source_name.lower())
        if source_best:
            source_e1rm = _get_e1rm(source_best)
            if source_e1rm and source_e1rm > 0:
                inferred_e1rm = source_e1rm * ratio
                load = _load_from_e1rm(inferred_e1rm, target_reps, target_rpe)
                conservative = 0.90 * (0.90 if is_beginner else 1.0)
                load *= conservative
                return {
                    'recommended_load_kg': _round_to_increment(load, increment),
                    'recommendation_source': 'inferred',
                    'recommendation_note': (
                        f"Estimated from your {source_name} — adjust freely"
                    ),
                }

    return _NO_DATA


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_from_e1rm(e1rm, target_reps, target_rpe):
    """
    Epley reverse:  load = e1rm / (1 + effective_reps / 30)
    effective_reps = target_reps + RIR  (RIR = 10 - target_rpe)
    """
    rir = max(0.0, 10.0 - float(target_rpe))
    effective_reps = float(target_reps) + rir
    if effective_reps <= 0:
        return e1rm
    return e1rm / (1.0 + effective_reps / 30.0)


def _get_e1rm(best):
    """Extract or calculate e1RM from an Exercise_Bests row."""
    e1rm = _parse_float(best.get('strength_e1rm_kg'))
    if e1rm and e1rm > 0:
        return e1rm
    # Fallback: calculate via Epley from raw load + reps
    load = _parse_float(best.get('strength_load_kg'))
    reps = _parse_float(best.get('strength_reps'))
    if load and reps and reps > 0:
        return load * (1.0 + reps / 30.0)
    return None


def _increment_for(exercise_name):
    """Return the rounding increment (kg) appropriate for the exercise type."""
    name = exercise_name.lower()
    if any(k in name for k in ('barbell', 'back squat', 'deadlift',
                               'bench press', 'overhead press')):
        return 2.5
    if 'dumbbell' in name:
        return 2.0
    if any(k in name for k in ('cable', 'machine', 'lat pulldown', 'leg press')):
        return 2.5
    return 1.0


def _round_to_increment(value, increment):
    """Round value to the nearest increment, to 2 decimal places."""
    if not value or increment <= 0:
        return value
    return round(round(value / increment) * increment, 2)


def _parse_float(val):
    """Safe float parse, returns None on failure or NaN."""
    if val is None or val == '':
        return None
    try:
        result = float(val)
        return result if result == result else None  # NaN guard
    except (ValueError, TypeError):
        return None


def _parse_target_reps(step):
    """Extract the primary target reps from step data."""
    reps = _parse_float(step.get('reps'))
    if reps and reps > 0:
        return int(reps)
    # Try first value of reps_pattern e.g. "8,8,6" → 8
    pattern = str(step.get('reps_pattern', '') or '').strip()
    if pattern:
        parts = pattern.replace('-', ',').replace('/', ',').split(',')
        first = _parse_float(parts[0].strip()) if parts else None
        if first and first > 0:
            return int(first)
    return None


def _parse_target_rpe(step):
    """Extract the target RPE. Use the last (hardest) set's RPE for conservatism."""
    rpe_pattern = str(step.get('rpe_pattern', '') or '').strip()
    if rpe_pattern:
        parts = rpe_pattern.replace('-', ',').replace('/', ',').split(',')
        last = _parse_float(parts[-1].strip()) if parts else None
        if last:
            return float(last)
    # Fall back to target_value when target_type is rpe
    if str(step.get('target_type', '') or '').lower() == 'rpe':
        val = str(step.get('target_value', '') or '')
        if '-' in val:
            bounds = val.split('-')
            nums = [_parse_float(b.strip()) for b in bounds]
            nums = [n for n in nums if n is not None]
            if nums:
                return sum(nums) / len(nums)
        return _parse_float(val)
    return None


def _is_beginner(client_profile):
    """True if client is beginner / novice (conservative load reduction applies)."""
    exp = str(client_profile.get('training_experience', '') or '').lower()
    return exp in ('beginner', 'novice', 'new')
