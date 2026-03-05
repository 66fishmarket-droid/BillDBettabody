"""exercise_mapper.py — Map Garmin exercise name strings to FIT numeric codes.

Builds a lookup dict at module load from Profile['types'] in profile.py so
that exercise names stored in Exercises_Library.garmin_exercise_name can be
translated to the (exercise_category, exercise_name) integer pair needed in
FIT workout_step messages.

Normalisation convention
    Profile: 'barbell_back_squat' (underscores, lowercase)
    Sheet:   'Barbell Back Squat'  (spaces, title-case)
    Both normalise to: 'barbell back squat' (replace _ with space, .lower())

Example
    lookup_exercise('Barbell Back Squat') → (28, 6)
    # 28 = squat category, 6 = barbell_back_squat within that category
"""

from .profile import Profile


def _normalise(name: str) -> str:
    return name.replace('_', ' ').lower().strip()


def _build_exercise_lookup() -> dict:
    """Build {normalised_display_name: (category_num, exercise_name_num)}.

    Iterates Profile['types']['exercise_category'] for category numbers,
    then looks up each category's exercise name list from
    Profile['types']['{category_name}_exercise_name'].
    """
    lookup: dict[str, tuple[int, int]] = {}
    types = Profile.get('types', {})
    cat_type = types.get('exercise_category', {})

    for num_str, cat_name in cat_type.items():
        # Skip hex-prefixed sentinel values (e.g. '0x...') and unknown
        if num_str.startswith('0x') or cat_name == 'unknown':
            continue
        try:
            cat_num = int(num_str)
        except ValueError:
            continue

        exercise_type_key = f'{cat_name}_exercise_name'
        exercise_type = types.get(exercise_type_key, {})

        for ex_num_str, ex_name in exercise_type.items():
            try:
                ex_num = int(ex_num_str)
            except ValueError:
                continue

            normalised = _normalise(ex_name)
            # First match wins (lowest category num, then lowest exercise num in
            # iteration order). Duplicate names across categories are rare.
            if normalised not in lookup:
                lookup[normalised] = (cat_num, ex_num)

    return lookup


# Built once on first import; profile.py is auto-generated and never changes at runtime.
_EXERCISE_LOOKUP: dict[str, tuple[int, int]] = _build_exercise_lookup()


def lookup_exercise(garmin_exercise_name: str) -> tuple[int | None, int | None]:
    """Return (category_num, exercise_name_num) for a Garmin exercise name string.

    Args:
        garmin_exercise_name: Value from Exercises_Library.garmin_exercise_name column,
                              e.g. 'Barbell Back Squat'.

    Returns:
        (category_num, exercise_name_num) if found, else (None, None).
    """
    if not garmin_exercise_name:
        return None, None
    normalised = _normalise(str(garmin_exercise_name))
    return _EXERCISE_LOOKUP.get(normalised, (None, None))
