"""workout_builder.py — Build a FIT workout file from a Bill session + steps.

Takes a session dict (from Plans_Sessions) and a list of step dicts (from
Plans_Steps) and returns raw .fit file bytes that can be downloaded and synced
to a Garmin device.

Tracking tags embedded for future import matching:
  workout.wkt_description = "SID:{session_id}"
  workout_step.notes       = "STID:{step_id}"  (last set of each exercise only)
"""

import re
import time

from .encoder import FitEncoder
from .exercise_mapper import lookup_exercise
from .fit import BASE_TYPE_DEFINITIONS, BASE_TYPE
from .util import FIT_EPOCH_S


# ── FIT base-type constants used throughout ───────────────────────────────────
_BT_ENUM   = BASE_TYPE['ENUM']    # 0x00  size=1  invalid=0xFF
_BT_UINT16 = BASE_TYPE['UINT16']  # 0x04  size=2  invalid=0xFFFF
_BT_UINT32 = BASE_TYPE['UINT32']  # 0x06  size=4  invalid=0xFFFFFFFF
_BT_STRING = BASE_TYPE['STRING']  # 0x07  size=1/char

_INV_ENUM   = BASE_TYPE_DEFINITIONS[_BT_ENUM]['invalid']    # 0xFF
_INV_UINT16 = BASE_TYPE_DEFINITIONS[_BT_UINT16]['invalid']  # 0xFFFF
_INV_UINT32 = BASE_TYPE_DEFINITIONS[_BT_UINT32]['invalid']  # 0xFFFFFFFF

# ── FIT intensity values (Profile['types']['intensity']) ──────────────────────
_INTENSITY_ACTIVE   = 0
_INTENSITY_REST     = 1
_INTENSITY_WARMUP   = 2
_INTENSITY_COOLDOWN = 3
_INTENSITY_RECOVERY = 4
_INTENSITY_INTERVAL = 5

# ── FIT wkt_step_duration values ──────────────────────────────────────────────
_DUR_TIME = 0   # duration_value in ms (scale × 1000)
_DUR_OPEN = 5   # no duration constraint
_DUR_REPS = 29  # duration_value = rep count

# ── FIT wkt_step_target values ────────────────────────────────────────────────
_TGT_HEART_RATE = 1
_TGT_OPEN       = 2

# ── FIT sport / sub_sport values ─────────────────────────────────────────────
_SPORT_RUNNING          = 1
_SPORT_FITNESS_EQUIP    = 4   # used for strength sessions
_SUBSPORT_GENERIC       = 0
_SUBSPORT_STRENGTH      = 20  # Profile['types']['sub_sport']['20'] = 'strength_training'

# ── Field string sizes (includes null terminator) ────────────────────────────
_WKT_NAME_SIZE  = 49   # 48 usable chars
_WKT_DESC_SIZE  = 64   # 63 usable chars  (fits "SID:" + any reasonable ID)
_STEP_NAME_SIZE = 32   # 31 usable chars
_NOTES_SIZE     = 32   # 31 usable chars  (fits "STID:" + step_id)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_int(v, default: int = 0) -> int:
    """Convert a value from Google Sheets (may be str, float, empty) to int."""
    if v is None or v == '':
        return default
    try:
        return int(float(str(v)))
    except (ValueError, TypeError):
        return default


def _safe_float(v, default=None):
    if v is None or v == '':
        return default
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return default


def _parse_reps(v) -> int:
    """Extract a rep count from a field that may be '8', '8-12', '8 reps', etc."""
    if v is None or v == '':
        return 1
    m = re.search(r'\d+', str(v))
    return int(m.group()) if m else 1


def _parse_hr_zone(v) -> int | None:
    """Parse an HR zone number from strings like 'zone 2', 'Z2', '2'."""
    if v is None or v == '':
        return None
    m = re.search(r'\d+', str(v).lower())
    return int(m.group()) if m else None


def _encode_weight(load_kg) -> int | None:
    """Convert kg to exercise_weight raw units (0.01 kg increments → × 100)."""
    if load_kg is None:
        return None
    w = int(round(float(load_kg) * 100))
    if w < 0 or w > 65534:
        return None
    return w


def _segment_intensity(segment_type: str) -> int:
    st = segment_type.lower().strip()
    if st == 'warmup':
        return _INTENSITY_WARMUP
    if st == 'cooldown':
        return _INTENSITY_COOLDOWN
    return _INTENSITY_ACTIVE


def _is_interval(step: dict) -> bool:
    count = _safe_int(step.get('interval_count'), 0)
    work  = _safe_int(step.get('interval_work_sec'), 0)
    return count > 0 and work > 0


# ─────────────────────────────────────────────────────────────────────────────
# Step counting (pre-pass to populate num_valid_steps before writing steps)
# ─────────────────────────────────────────────────────────────────────────────

def _count_steps(steps: list) -> int:
    """Count the total number of workout_step records that will be written."""
    total = 0
    for step in steps:
        step_type = str(step.get('step_type', '')).lower()
        if step_type == 'strength':
            sets = max(1, _safe_int(step.get('sets'), 1))
            # sets active records + (sets-1) rest records
            total += sets + max(0, sets - 1)
        elif step_type == 'cardio' and _is_interval(step):
            n = max(1, _safe_int(step.get('interval_count'), 1))
            total += n * 2  # n work + n recovery
        else:
            total += 1  # warmup, cooldown, mobility, steady run — single step
    return total


# ─────────────────────────────────────────────────────────────────────────────
# Low-level step writer
# ─────────────────────────────────────────────────────────────────────────────

def _write_wkt_step(
    enc: FitEncoder,
    step_name,
    duration_type: int,
    duration_value,
    target_type: int,
    target_value,
    intensity: int,
    notes,
    exercise_category,
    exercise_name_num,
    exercise_weight,
) -> None:
    """Write one workout_step data record (local message 2)."""
    enc.write_message(2, [
        enc.encode_value(step_name,        _BT_STRING, _STEP_NAME_SIZE),
        enc.encode_value(duration_type,    _BT_ENUM),
        enc.encode_value(duration_value,   _BT_UINT32),
        enc.encode_value(target_type,      _BT_ENUM),
        enc.encode_value(target_value,     _BT_UINT32),
        enc.encode_value(intensity,        _BT_ENUM),
        enc.encode_value(notes,            _BT_STRING, _NOTES_SIZE),
        enc.encode_value(exercise_category, _BT_UINT16),
        enc.encode_value(exercise_name_num, _BT_UINT16),
        enc.encode_value(exercise_weight,   _BT_UINT16),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Per-step-type writers
# ─────────────────────────────────────────────────────────────────────────────

def _write_strength_step(enc: FitEncoder, step: dict, garmin_mappings: dict) -> None:
    """Expand a strength step into (sets × active) + ((sets-1) × rest) records."""
    exercise_name = str(step.get('exercise_name') or '')
    step_id       = str(step.get('step_id') or '')
    segment_type  = str(step.get('segment_type') or 'main')

    cat_num, ex_num   = garmin_mappings.get(exercise_name, (None, None))
    load_kg           = _safe_float(step.get('load_kg'))
    exercise_weight   = _encode_weight(load_kg)

    sets     = max(1, _safe_int(step.get('sets'), 1))
    reps     = max(1, _parse_reps(step.get('reps')))
    rest_ms  = _safe_int(step.get('rest_seconds'), 60) * 1000

    intensity = _segment_intensity(segment_type)

    for set_num in range(1, sets + 1):
        is_last   = (set_num == sets)
        step_name = f'{exercise_name} {set_num}/{sets}'
        notes     = f'STID:{step_id}' if is_last else None

        _write_wkt_step(
            enc,
            step_name        = step_name,
            duration_type    = _DUR_REPS,
            duration_value   = reps,
            target_type      = _TGT_OPEN,
            target_value     = None,        # open → invalid sentinel
            intensity        = intensity,
            notes            = notes,
            exercise_category = cat_num,
            exercise_name_num = ex_num,
            exercise_weight   = exercise_weight,
        )

        if not is_last and rest_ms > 0:
            _write_wkt_step(
                enc,
                step_name         = 'Rest',
                duration_type     = _DUR_TIME,
                duration_value    = rest_ms,
                target_type       = _TGT_OPEN,
                target_value      = None,
                intensity         = _INTENSITY_REST,
                notes             = None,
                exercise_category = None,
                exercise_name_num = None,
                exercise_weight   = None,
            )


def _write_interval_step(enc: FitEncoder, step: dict) -> None:
    """Expand a cardio interval step into N × (work + recovery) records."""
    step_id       = str(step.get('step_id') or '')
    exercise_name = str(step.get('exercise_name') or 'Interval')
    segment_type  = str(step.get('segment_type') or 'main')

    n         = max(1, _safe_int(step.get('interval_count'), 1))
    work_ms   = _safe_int(step.get('interval_work_sec'), 0) * 1000
    rest_ms   = _safe_int(step.get('interval_rest_sec'), 0) * 1000
    hr_zone   = _parse_hr_zone(step.get('target_value') or step.get('intended_hr_zone'))

    target_type  = _TGT_HEART_RATE if hr_zone is not None else _TGT_OPEN
    target_value = hr_zone if hr_zone is not None else None

    for i in range(1, n + 1):
        is_last   = (i == n)
        work_name = f'{exercise_name} {i}/{n}'
        notes     = f'STID:{step_id}' if is_last else None

        _write_wkt_step(
            enc,
            step_name         = work_name,
            duration_type     = _DUR_TIME,
            duration_value    = work_ms if work_ms > 0 else None,
            target_type       = target_type,
            target_value      = target_value,
            intensity         = _INTENSITY_INTERVAL,
            notes             = notes,
            exercise_category = None,
            exercise_name_num = None,
            exercise_weight   = None,
        )

        _write_wkt_step(
            enc,
            step_name         = 'Recovery',
            duration_type     = _DUR_TIME,
            duration_value    = rest_ms if rest_ms > 0 else None,
            target_type       = _TGT_OPEN,
            target_value      = None,
            intensity         = _INTENSITY_RECOVERY,
            notes             = None,
            exercise_category = None,
            exercise_name_num = None,
            exercise_weight   = None,
        )


def _write_single_step(enc: FitEncoder, step: dict) -> None:
    """Write a single workout_step for warmup, cooldown, mobility or steady run."""
    step_id       = str(step.get('step_id') or '')
    exercise_name = str(step.get('exercise_name') or 'Step')
    segment_type  = str(step.get('segment_type') or '').lower()
    step_type     = str(step.get('step_type') or '').lower()

    intensity = _segment_intensity(segment_type)

    # Duration: use the step's duration_value (treated as seconds) if present
    raw_dv = step.get('duration_value')
    secs   = _safe_float(raw_dv)
    if secs and secs > 0:
        duration_type  = _DUR_TIME
        duration_value = int(secs * 1000)  # ms
    else:
        duration_type  = _DUR_OPEN
        duration_value = None

    # HR zone target for running/cardio steps
    hr_zone      = _parse_hr_zone(step.get('target_value') or step.get('intended_hr_zone'))
    target_type  = _TGT_HEART_RATE if (step_type == 'cardio' and hr_zone is not None) else _TGT_OPEN
    target_value = hr_zone if target_type == _TGT_HEART_RATE else None

    _write_wkt_step(
        enc,
        step_name         = exercise_name,
        duration_type     = duration_type,
        duration_value    = duration_value,
        target_type       = target_type,
        target_value      = target_value,
        intensity         = intensity,
        notes             = f'STID:{step_id}' if step_id else None,
        exercise_category = None,
        exercise_name_num = None,
        exercise_weight   = None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_workout_fit(session: dict, steps: list, garmin_mappings: dict) -> bytes:
    """Build a FIT workout file from a Bill session + steps.

    Args:
        session:         Dict with at least 'session_id' and 'focus' keys.
        steps:           List of step dicts from Plans_Steps (already sorted by
                         step_order).  Each step should have: step_id,
                         exercise_name, step_type, segment_type, sets, reps,
                         load_kg, rest_seconds, interval_count,
                         interval_work_sec, interval_rest_sec,
                         target_value, intended_hr_zone, duration_value.
        garmin_mappings: {exercise_name: (category_num, name_num)} — from
                         lookup_exercise() applied to sheets garmin data.

    Returns:
        Raw .fit file bytes.
    """
    # ── Sport detection ───────────────────────────────────────────────────────
    def _is_running_step(s: dict) -> bool:
        st = str(s.get('step_type', '')).lower()
        ex = str(s.get('exercise_name', '')).lower()
        return st == 'cardio' and any(kw in ex for kw in ('run', 'jog', 'walk'))

    if any(_is_running_step(s) for s in steps):
        sport     = _SPORT_RUNNING
        sub_sport = _SUBSPORT_GENERIC
    else:
        sport     = _SPORT_FITNESS_EQUIP
        sub_sport = _SUBSPORT_STRENGTH

    # ── Pre-pass: count total workout_step records ────────────────────────────
    total_steps = _count_steps(steps)

    # ── Workout name + tracking tags ──────────────────────────────────────────
    focus          = str(session.get('focus') or 'Workout')
    wkt_name       = focus[:48]
    session_id     = str(session.get('session_id') or '')
    wkt_description = f'SID:{session_id}'

    # ── FIT timestamp ─────────────────────────────────────────────────────────
    fit_ts = int(time.time()) - FIT_EPOCH_S

    enc = FitEncoder()

    # ── file_id (local=0, global=0) ───────────────────────────────────────────
    enc.define_message(0, 0, [
        (0, 1, _BT_ENUM),   # type: file enum; 5 = workout
        (4, 4, _BT_UINT32), # time_created: FIT timestamp
    ])
    enc.write_message(0, [
        enc.encode_value(5,      _BT_ENUM),    # workout file type
        enc.encode_value(fit_ts, _BT_UINT32),
    ])

    # ── workout (local=1, global=26) ──────────────────────────────────────────
    enc.define_message(1, 26, [
        (4,  1,              _BT_ENUM),    # sport
        (6,  2,              _BT_UINT16),  # num_valid_steps
        (8,  _WKT_NAME_SIZE, _BT_STRING),  # wkt_name  (shown on watch)
        (11, 1,              _BT_ENUM),    # sub_sport
        (17, _WKT_DESC_SIZE, _BT_STRING),  # wkt_description  (SID tag)
    ])
    enc.write_message(1, [
        enc.encode_value(sport,           _BT_ENUM),
        enc.encode_value(total_steps,     _BT_UINT16),
        enc.encode_value(wkt_name,        _BT_STRING, _WKT_NAME_SIZE),
        enc.encode_value(sub_sport,       _BT_ENUM),
        enc.encode_value(wkt_description, _BT_STRING, _WKT_DESC_SIZE),
    ])

    # ── workout_step (local=2, global=27) — define schema once ───────────────
    enc.define_message(2, 27, [
        (0,  _STEP_NAME_SIZE, _BT_STRING),  # wkt_step_name
        (1,  1,               _BT_ENUM),    # duration_type
        (2,  4,               _BT_UINT32),  # duration_value
        (3,  1,               _BT_ENUM),    # target_type
        (4,  4,               _BT_UINT32),  # target_value
        (7,  1,               _BT_ENUM),    # intensity
        (8,  _NOTES_SIZE,     _BT_STRING),  # notes  (STID tag)
        (10, 2,               _BT_UINT16),  # exercise_category
        (11, 2,               _BT_UINT16),  # exercise_name
        (12, 2,               _BT_UINT16),  # exercise_weight (0.01 kg units)
    ])

    # ── Write step records ────────────────────────────────────────────────────
    for step in steps:
        step_type = str(step.get('step_type', '')).lower()

        if step_type == 'strength':
            _write_strength_step(enc, step, garmin_mappings)
        elif step_type == 'cardio' and _is_interval(step):
            _write_interval_step(enc, step)
        else:
            _write_single_step(enc, step)

    return enc.get_bytes()
