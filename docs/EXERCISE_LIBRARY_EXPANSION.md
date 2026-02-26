# Exercise Library Expansion — Process Guide

## Overview

The exercise library lives entirely in the `Exercises_Library` tab of the Google Sheet.
Claude can read it, generate new exercises, and write them directly using the service account.
You review before anything is written, then add YouTube URLs manually in the sheet afterwards.

---

## Starting a Session

Just open Claude Code and say something like:

> "Let's do this week's exercise batch"

Claude will run `exercise_lib.py summary` and `max-id` to read the current state of the sheet
before generating anything. No need to export or share data manually.

---

## The Weekly Workflow

```
1. Claude reads the sheet   →   sees current gaps and IDs
2. Claude generates 10      →   shows you a review table
3. You approve (or tweak)   →   confirm names, taxonomy, difficulty
4. Claude writes to sheet   →   single batch write, no manual copy-paste
5. You add YouTube URLs     →   search by exercise name in the sheet
```

---

## Management Script

Located at `backend/scripts/exercise_lib.py`. Always run from the `backend/` directory.

```bash
# Check highest IDs and total count
python scripts/exercise_lib.py max-id

# Distribution breakdown by category, body_region, movement_pattern, etc.
python scripts/exercise_lib.py summary

# Dump all exercises as JSON (for deep analysis)
python scripts/exercise_lib.py read

# Write a batch of exercises from a JSON file
python scripts/exercise_lib.py append scripts/pending_exercises.json
```

The append command:
- Writes all rows in a **single API call** (important — see Gotchas below)
- Always leaves `video_url` blank
- Defaults `status` to `active` and `last_verified_date` to today if not supplied
- Skips any exercise whose `exercise_name` already exists (case-insensitive)

---

## ID Scheme

| Prefix | Used for | Current max |
|--------|----------|-------------|
| `ex_XXXX` | All individual exercises | `ex_0298` |
| `wu_XXXX` | Compound warmup routines (e.g. "Lower Body Dynamic Prep") | `wu_0007` |
| `cd_XXXX` | Compound cooldown routines | `cd_0005` |

### Available gap IDs (as of Feb 2026)

The original library used ID ranges to group exercises by movement pattern. Those gaps are
now free to use since taxonomy fields handle grouping.

| Gap range | Slots | Natural fit |
|-----------|-------|-------------|
| `ex_0015–0019` | 5 | Extra squat/lower body |
| `ex_0033–0039` | 7 | Extra hinge |
| `ex_0053–0059` | 7 | Extra push_horizontal |
| `ex_0073–0079` | 7 | Extra pull_horizontal |
| `ex_0092–0099` | 8 | Extra push_vertical |
| `ex_0113–0119` | 7 | Extra pull_vertical |
| `ex_0132–0139` | 8 | Extra core |
| `ex_0154–0159` | 6 | Extra conditioning/locomotion |
| `ex_0176–0179` | 4 | Swimming-adjacent |
| **`ex_0193–0286`** | **94** | **New categories — running drills, plyometrics, etc.** |

New batches should use the large `ex_0193+` block unless an exercise clearly belongs
in one of the smaller movement-pattern gaps above.

---

## Taxonomy Reference

These are the accepted values for the key categorical fields. Stay consistent —
Claude will use the existing values when generating new exercises.

### `category`
`strength` · `conditioning` · `mobility` · `core` · `power` · `swimming`

### `body_region`
`upper` · `lower` · `full` · `core`

### `movement_pattern`
`squat` · `lunge` · `hinge` · `push_horizontal` · `push_vertical`
`pull_horizontal` · `pull_vertical` · `gait` · `locomotion` · `plyometric`
`rotation` · `anti_extension` · `anti_lateral_flexion` · `anti_rotation`

### `segment_type`
`warmup` · `main` · `cooldown` · `warmup; main` *(semi-colon separated for multi)*

### `equipment`
`bodyweight` · `free_weight` · `fixed_machine` · `cable_system` · `portable_accessory`
`cardio_machine` · `pool` · `environmental` · `household` · `human_powered_vehicle`

### `locomotion_type`
`none` · `running` · `walking` · `skipping` · `lateral` · `jumping`

### `difficulty`
`beginner` · `intermediate` · `advanced`

### `load_type`
`bodyweight_only` · `free_weight` · `machine` · `band`

### `execution_style`
`bilateral` · `unilateral_alternating` · `unilateral_single` · `cyclical`

### `tempo_emphasis`
`controlled` · `fast` · `explosive` · `slow`

### `environment`
`indoor` · `outdoor` · `pool`

### `metric_family_default`
`calisthenics` *(rep-based)* · `duration` *(time-based)* · `distance` *(distance-based)*

---

## Planned Batches (4-week starter)

| Week | Theme | ID range |
|------|-------|----------|
| ✅ 1 | Running warmup drills | `ex_0193–0202` |
| 2 | Plyometrics | `ex_0203–0212` |
| 3 | Cooldown stretches | `cd_0006–0015` |
| 4 | Running conditioning variants | `ex_0213–0222` |

---

## Gotchas

**Never call `append_row` in a loop.**
The Google Sheets API's table-detection drifts with each call and offsets each row further
right. The script uses `append_rows` (plural) in a single call — do not change this.

**Delete pre-created blank rows before appending.**
If you have empty placeholder rows inside the table range, the API detects them as the
"end of table" and writes into them incorrectly. Either delete blank rows first, or ask
Claude to clear them before running a batch.

**`pending_exercises.json` is temporary.**
Claude writes this file, uses it, then deletes it. It is not committed. If a session
ends before the append runs, Claude will need to regenerate it.

**YouTube URLs are always left blank by the script.**
Add them manually in the sheet after reviewing options on YouTube. The frontend supports
multiple URLs per exercise — enter each on its own line in the cell (Alt+Enter in Sheets).

---

## Full Column Reference

In order, as they appear in the sheet:

`exercise_id` · `exercise_name` · `name_canonical` · `category` · `body_region`
`equipment` · `variant` · `movement_pattern` · `primary_muscles` · `video_url`
`image_url` · `coaching_cues_short` · `exercise_description_short`
`exercise_description_long` · `safety_notes` · `common_mistakes` · `regression`
`progression` · `source_url` · `last_verified_date` · `status`
`metric_family_default` · `garmin_exercise_name` · `garmin_mapping_confidence`
`garmin_variations` · `segment_type` · `training_focus` · `secondary_muscles`
`difficulty` · `load_type` · `execution_style` · `tempo_emphasis` · `body_position`
`environment` · `locomotion_type` · `special_flags`
