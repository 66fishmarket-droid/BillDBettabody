"""
One-off migration script — 2026-02-23

Does two things:
  1. Adds 10 missing exercises to Exercises_Library (Category B)
  2. Fixes 6 exercise name mismatches in Plans_Steps (Category A)

Run from the backend/ directory:
    cd backend
    python scripts/migrate_exercise_names.py

Idempotent: checks before writing — safe to run more than once.
"""

import os
import sys
from datetime import date

from dotenv import load_dotenv

# Load .env from backend/
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import gspread
from google.oauth2.service_account import Credentials

# ── Auth ──────────────────────────────────────────────────────────────────────

_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def _connect():
    sa_json       = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']
    spreadsheet_id = os.environ['GOOGLE_SHEETS_SPREADSHEET_ID']
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id)


# ── Category B — new exercises ─────────────────────────────────────────────────

TODAY = date.today().strftime('%d/%m/%Y')

NEW_EXERCISES = [
    {
        'exercise_id':              'ex_0290',
        'exercise_name':            'Calf Raises',
        'name_canonical':           'calf_raise',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'bodyweight,barbell,dumbbell',
        'variant':                  'standard',
        'movement_pattern':         'push',
        'primary_muscles':          'gastrocnemius,soleus',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Full range — all the way up, all the way down. Pause at the top. Control the descent.',
        'exercise_description_short': 'Ankle plantar flexion movement targeting the gastrocnemius and soleus.',
        'exercise_description_long':  (
            'Stand on a step edge or flat surface. Rise onto the balls of your feet as high as '
            'possible by fully contracting the calves, then lower your heels below the step for '
            'full stretch. Can be loaded with a barbell, dumbbells, or performed on a dedicated '
            'calf raise machine. Performing on a step edge greatly increases the range of motion '
            'and training stimulus. Single-leg variation increases difficulty and addresses '
            'side-to-side imbalances.'
        ),
        'safety_notes':             'Avoid bouncing out of the bottom. Maintain controlled dorsiflexion — do not drop suddenly.',
        'common_mistakes':          'Short range of motion; rushing the eccentric; not achieving full plantar flexion.',
        'regression':               'Seated Calf Raise Machine',
        'progression':              'Single-Leg Calf Raise',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Calf Press',
        'garmin_mapping_confidence':'close',
        'garmin_variations':        'Calf Press; Single Leg Calf Press; Donkey Calf Raise',
        'segment_type':             'main',
        'training_focus':           'hypertrophy',
        'secondary_muscles':        'tibialis_anterior',
        'difficulty':               'beginner',
        'load_type':                'weighted',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'slow_eccentric',
        'body_position':            'standing',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'joint_friendly',
    },
    {
        'exercise_id':              'ex_0291',
        'exercise_name':            'Lying Leg Curls',
        'name_canonical':           'lying_leg_curl',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'machine',
        'variant':                  'prone',
        'movement_pattern':         'hinge',
        'primary_muscles':          'hamstrings',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Curl all the way up. Squeeze at the top. Slow the lowering.',
        'exercise_description_short': 'Prone machine knee flexion isolating the hamstrings.',
        'exercise_description_long':  (
            'Lie face down on the lying leg curl machine with the ankle roller pad just above '
            'your heels and your knees just off the edge of the pad. Grasp the handles for '
            'stability. Curl both legs toward your glutes through a full range of motion, '
            'pause briefly at the top, then lower under control to full extension. Keep hips '
            'pressed into the pad throughout — do not let them rise.'
        ),
        'safety_notes':             'Keep hips flat on the pad throughout. Do not arch the lower back to assist the curl.',
        'common_mistakes':          'Using momentum; hips rising off the pad; not reaching full extension at the bottom.',
        'regression':               'Glute Bridge',
        'progression':              'Single-Leg Lying Leg Curl',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Leg Curl',
        'garmin_mapping_confidence':'close',
        'garmin_variations':        'Leg Curl; Single Leg Curl',
        'segment_type':             'main',
        'training_focus':           'hypertrophy',
        'secondary_muscles':        'gastrocnemius',
        'difficulty':               'beginner',
        'load_type':                'machine_load',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'slow_eccentric',
        'body_position':            'prone',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            '',
    },
    {
        'exercise_id':              'ex_0292',
        'exercise_name':            'Leg Extension Machine',
        'name_canonical':           'leg_extension',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'machine',
        'variant':                  'machine',
        'movement_pattern':         'push',
        'primary_muscles':          'quads',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Extend fully. Squeeze the quads at the top. Controlled descent.',
        'exercise_description_short': 'Seated machine knee extension isolating the quadriceps.',
        'exercise_description_long':  (
            'Sit in the leg extension machine with the ankle roller just above your feet, back '
            'flat against the pad and knees at the edge of the seat. Extend both legs to full '
            'knee extension, squeezing the quads at the top, then lower under control to about '
            '90 degrees. Avoid swinging or using trunk momentum — the movement should be pure '
            'knee extension.'
        ),
        'safety_notes':             'Avoid locking out with excessive force. Those with patellofemoral issues should work within a pain-free range.',
        'common_mistakes':          'Swinging the torso; partial range of motion; foot rotation.',
        'regression':               'Terminal Knee Extension (band)',
        'progression':              'Pause Leg Extension',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Leg Extension',
        'garmin_mapping_confidence':'exact',
        'garmin_variations':        'Leg Extension; Single Leg Extension',
        'segment_type':             'main',
        'training_focus':           'hypertrophy',
        'secondary_muscles':        'hip_flexors',
        'difficulty':               'beginner',
        'load_type':                'machine_load',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'controlled',
        'body_position':            'seated',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'knee_dominant',
    },
    {
        'exercise_id':              'ex_0293',
        'exercise_name':            'Leg Press Machine',
        'name_canonical':           'leg_press',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'machine',
        'variant':                  'machine',
        'movement_pattern':         'squat',
        'primary_muscles':          'quads,glutes',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Drive through the whole foot. Keep lower back flat against the pad. Control the descent.',
        'exercise_description_short': 'Bilateral lower body push on a fixed-path machine.',
        'exercise_description_long':  (
            'Sit in the leg press machine with your feet shoulder-width apart on the platform '
            'and lower back fully supported by the pad. Release the safety handles and lower '
            'the platform under control until your knees approach 90 degrees or below, then '
            'drive through your feet to fully extend. Foot position can be varied — higher on '
            'the platform emphasises the glutes and hamstrings, lower increases quad demand.'
        ),
        'safety_notes':             'Do not allow the lower back to peel off the pad at the bottom of the movement. Keep knees tracking over toes.',
        'common_mistakes':          'Partial range of motion; knees caving inward; excessive foot placement variation without intent.',
        'regression':               'Goblet Squat',
        'progression':              'Hack Squat Machine',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Leg Press',
        'garmin_mapping_confidence':'exact',
        'garmin_variations':        'Leg Press; Single Leg Press; Calf Press On Leg Press',
        'segment_type':             'main',
        'training_focus':           'hypertrophy,strength',
        'secondary_muscles':        'hamstrings,adductors',
        'difficulty':               'beginner',
        'load_type':                'machine_load',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'controlled',
        'body_position':            'seated_reclined',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'knee_dominant,joint_friendly',
    },
    {
        'exercise_id':              'ex_0294',
        'exercise_name':            'Hack Squat Machine',
        'name_canonical':           'hack_squat_machine',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'machine',
        'variant':                  'machine',
        'movement_pattern':         'squat',
        'primary_muscles':          'quads,glutes',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Back against the pad throughout. Full depth — hip crease below the knee. Drive through the whole foot.',
        'exercise_description_short': 'Fixed-path machine squat with upright torso and high quad demand.',
        'exercise_description_long':  (
            'Step into the hack squat machine, positioning your shoulders under the pads and '
            'feet mid-platform hip-width apart. Release the safety bars and lower your hips '
            'by bending the knees until the hip crease passes the knee line, keeping the back '
            'flat against the pad throughout. Drive through your feet to extend back to the '
            'start. The upright torso position compared to a free squat places greater emphasis '
            'on the quads.'
        ),
        'safety_notes':             'Keep feet symmetrically placed. Do not hyperextend the knees at lockout. Ensure back pad provides full support.',
        'common_mistakes':          'Heels rising; not achieving full depth; locking out aggressively; knees caving inward.',
        'regression':               'Leg Press Machine',
        'progression':              'Back Squat',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Hack Squat',
        'garmin_mapping_confidence':'exact',
        'garmin_variations':        'Hack Squat; Barbell Hack Squat',
        'segment_type':             'main',
        'training_focus':           'hypertrophy,strength',
        'secondary_muscles':        'hamstrings,adductors',
        'difficulty':               'intermediate',
        'load_type':                'machine_load',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'controlled',
        'body_position':            'standing_inclined',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'knee_dominant',
    },
    {
        'exercise_id':              'ex_0295',
        'exercise_name':            'Seated Leg Curl Machine',
        'name_canonical':           'seated_leg_curl',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'machine',
        'variant':                  'seated',
        'movement_pattern':         'hinge',
        'primary_muscles':          'hamstrings',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Sit upright. Full range of motion. Slow the negative.',
        'exercise_description_short': 'Seated machine knee flexion targeting the hamstrings.',
        'exercise_description_long':  (
            'Sit upright in the seated leg curl machine with the thigh pad across the top of '
            'your legs and the ankle roller sitting on your heels. Curl your heels down and back '
            'toward the seat through a full range of motion, pause briefly, then return under '
            'control to full extension. The seated position stretches the hamstrings at a '
            'longer muscle length than the prone version, which may increase hypertrophic '
            'stimulus.'
        ),
        'safety_notes':             'Keep back against the pad. Avoid hyperextending the knees at the start of each rep.',
        'common_mistakes':          'Short range of motion; using momentum; slouching forward during the curl.',
        'regression':               'Lying Leg Curls',
        'progression':              'Nordic Curl',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Leg Curl',
        'garmin_mapping_confidence':'close',
        'garmin_variations':        'Leg Curl; Single Leg Curl',
        'segment_type':             'main',
        'training_focus':           'hypertrophy',
        'secondary_muscles':        'gastrocnemius',
        'difficulty':               'beginner',
        'load_type':                'machine_load',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'slow_eccentric',
        'body_position':            'seated',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            '',
    },
    {
        'exercise_id':              'ex_0296',
        'exercise_name':            'Cable Kick-Back',
        'name_canonical':           'cable_kickback',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'cable machine',
        'variant':                  'standing',
        'movement_pattern':         'hinge',
        'primary_muscles':          'glutes',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Keep the torso steady — only the hip moves. Squeeze the glute at the peak. Control the return.',
        'exercise_description_short': 'Standing cable hip extension isolating the glutes.',
        'exercise_description_long':  (
            'Attach an ankle cuff to a low cable pulley and secure it around one ankle. Stand '
            'facing the machine and hold the frame for balance, with a slight forward lean at '
            'the hips. Keeping a slight bend in the standing knee, drive the working leg '
            'straight back by extending at the hip until the glute is fully contracted, then '
            'return under control. Avoid rotating the pelvis or arching the lower back to '
            'increase range.'
        ),
        'safety_notes':             'Maintain a neutral lower back. Do not hyperextend the lumbar spine to gain additional range.',
        'common_mistakes':          'Using momentum; swinging the torso; not squeezing the glute at the top of the movement.',
        'regression':               'Glute Bridge',
        'progression':              'Hip Thrust',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Donkey Kick',
        'garmin_mapping_confidence':'close',
        'garmin_variations':        'Donkey Kick; Cable Hip Extension',
        'segment_type':             'main',
        'training_focus':           'hypertrophy',
        'secondary_muscles':        'hamstrings,lower_back',
        'difficulty':               'beginner',
        'load_type':                'cable_load',
        'execution_style':          'unilateral',
        'tempo_emphasis':           'controlled',
        'body_position':            'standing',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'unilateral,glute_dominant',
    },
    {
        'exercise_id':              'ex_0297',
        'exercise_name':            'Dumbbell Reverse Lunge',
        'name_canonical':           'db_reverse_lunge',
        'category':                 'strength',
        'body_region':              'lower',
        'equipment':                'dumbbells',
        'variant':                  'reverse',
        'movement_pattern':         'squat',
        'primary_muscles':          'quads,glutes',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Front shin stays vertical. Back knee hovers near the floor. Drive through the front heel to stand.',
        'exercise_description_short': 'Unilateral lower body exercise stepping backward into a lunge position.',
        'exercise_description_long':  (
            'Stand holding dumbbells at your sides with feet together. Take a large step '
            'backward with one foot, lowering the back knee toward the floor while keeping the '
            'front shin as vertical as possible. The front knee should track directly over the '
            'foot and the torso should remain upright. Drive through the front heel to return '
            'to standing. Alternate legs or complete all reps on one side before switching.'
        ),
        'safety_notes':             'Take a long enough step to keep the front knee from travelling past the toes. Keep the torso upright.',
        'common_mistakes':          'Front knee diving forward past toes; torso leaning excessively; step too short.',
        'regression':               'Split Squat',
        'progression':              'Bulgarian Split Squat',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'strength',
        'garmin_exercise_name':     'Reverse Lunge',
        'garmin_mapping_confidence':'close',
        'garmin_variations':        'Reverse Lunge; Weighted Reverse Lunge; Reverse Lunge With Reach',
        'segment_type':             'main',
        'training_focus':           'strength,hypertrophy',
        'secondary_muscles':        'hamstrings,adductors,core',
        'difficulty':               'intermediate',
        'load_type':                'weighted',
        'execution_style':          'unilateral',
        'tempo_emphasis':           'controlled',
        'body_position':            'standing',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'unilateral,knee_dominant',
    },
    {
        'exercise_id':              'cd_0005',
        'exercise_name':            'Thread the Needle Stretch',
        'name_canonical':           'thread_the_needle',
        'category':                 'mobility',
        'body_region':              'upper',
        'equipment':                'bodyweight',
        'variant':                  'standard',
        'movement_pattern':         'rotation',
        'primary_muscles':          'thoracic_spine,lats',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Let the eye lead the rotation. Breathe through the movement. Never force it.',
        'exercise_description_short': 'Thoracic rotation mobility drill performed on hands and knees.',
        'exercise_description_long':  (
            'Start on all fours with hands under shoulders and knees under hips. Place one hand '
            'behind your head. Rotate that elbow down and under your body toward the opposite '
            'hand, letting it slide along the floor, then open it up toward the ceiling as far '
            'as comfortable — following the movement with your eyes. The hips stay level '
            'throughout; only the thoracic spine rotates. Exhale on the way down, inhale as '
            'you open up.'
        ),
        'safety_notes':             'Move slowly and breathe. If you feel any sharp neck or shoulder pain, reduce the range of motion.',
        'common_mistakes':          'Rushing the movement; hips rotating; not rotating far enough in either direction.',
        'regression':               'Cat-Cow',
        'progression':              'Seated Thoracic Rotation',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'duration',
        'garmin_exercise_name':     '',
        'garmin_mapping_confidence':'none',
        'garmin_variations':        '',
        'segment_type':             'warmup; cooldown',
        'training_focus':           'mobility',
        'secondary_muscles':        'rotator_cuff,deltoids',
        'difficulty':               'beginner',
        'load_type':                'bodyweight_only',
        'execution_style':          'unilateral',
        'tempo_emphasis':           'slow',
        'body_position':            'quadruped',
        'environment':              'indoor',
        'locomotion_type':          'none',
        'special_flags':            'joint_friendly,shoulder_mobility',
    },
    {
        'exercise_id':              'ex_0298',
        'exercise_name':            'Run-Walk Intervals',
        'name_canonical':           'run_walk_intervals',
        'category':                 'cardio',
        'body_region':              'full_body',
        'equipment':                'bodyweight',
        'variant':                  'intervals',
        'movement_pattern':         'gait',
        'primary_muscles':          'quads,glutes,calves,hamstrings',
        'video_url':                '',
        'image_url':                '',
        'coaching_cues_short':      'Comfortable running pace — you should be able to speak. Walk recoveries are brisk, not shuffling.',
        'exercise_description_short': 'Alternating running and walking intervals for building aerobic base.',
        'exercise_description_long':  (
            'Alternate between running and walking for prescribed intervals, e.g. 1 min run / '
            '2 min walk, repeated for the session duration. The running pace should be '
            'conversational — if you cannot speak in short sentences, slow down. Walk '
            'recoveries are active (brisk walk) rather than a shuffle. As fitness improves, '
            'the work-to-rest ratio is gradually shifted toward more running and less walking. '
            'Can be performed outdoors or on a treadmill.'
        ),
        'safety_notes':             'Never push the running pace to breathlessness. Extend walk intervals as needed. Warm up with 2-3 min brisk walk before the first run interval.',
        'common_mistakes':          'Running too fast during work intervals; cutting walk recoveries short; skipping the warm-up.',
        'regression':               'Treadmill Walk',
        'progression':              'Jogging',
        'source_url':               '',
        'last_verified_date':       TODAY,
        'status':                   'active',
        'metric_family_default':    'distance',
        'garmin_exercise_name':     'Run',
        'garmin_mapping_confidence':'close',
        'garmin_variations':        'Run; Walk; Run/Walk',
        'segment_type':             'main',
        'training_focus':           'aerobic',
        'secondary_muscles':        'core,hip_flexors',
        'difficulty':               'beginner',
        'load_type':                'bodyweight_only',
        'execution_style':          'bilateral',
        'tempo_emphasis':           'varied',
        'body_position':            'standing',
        'environment':              'outdoor,indoor',
        'locomotion_type':          'walking,running',
        'special_flags':            'low_impact,cardio_aerobic',
    },
]


# ── Category A — renames in Plans_Steps ────────────────────────────────────────

RENAMES = {
    'Barbell Row':           'Barbell Bent-Over Row',
    'Treadmill Walking':     'Treadmill Walk',
    'Elliptical':            'Elliptical Trainer',
    'Warmup \u2013 Elliptical': 'Warmup - Elliptical',   # en-dash → hyphen
    'Outdoor Walk':          'Walking',
    'Recovery Walk':         'Walking',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def col_letter(n):
    """Convert 1-based column index to A1-notation letter."""
    result = ''
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


# ── Part 1: Add exercises to Exercises_Library ────────────────────────────────

def add_library_exercises(spreadsheet):
    ws       = spreadsheet.worksheet('Exercises_Library')
    all_rows = ws.get_all_values()
    headers  = all_rows[0]

    try:
        name_col_idx = headers.index('exercise_name')
    except ValueError:
        print('  ERROR: exercise_name column not found in Exercises_Library')
        return

    print(f'  Sheet currently has {len(all_rows)} rows (header + {len(all_rows)-1} data rows)')
    # Show last 3 rows for diagnostics
    for i, r in enumerate(all_rows[-3:], start=len(all_rows) - 2):
        ex_id   = r[0] if r else '(empty)'
        ex_name = r[name_col_idx] if len(r) > name_col_idx else '(empty)'
        print(f'    Row {i}: id={ex_id} | name={ex_name}')

    # Clean up any test rows from previous debugging sessions
    while all_rows and len(all_rows) > 1:
        last_row = all_rows[-1]
        last_name = str(last_row[name_col_idx]).strip() if len(last_row) > name_col_idx else ''
        if 'test' in last_name.lower():
            last_row_num = len(all_rows)
            print(f'  Removing test row {last_row_num}: "{last_name}"')
            ws.delete_rows(last_row_num)
            all_rows.pop()
        else:
            break

    # Build existing names from clean data
    existing_names = {
        str(r[name_col_idx]).strip().lower()
        for r in all_rows[1:]
        if len(r) > name_col_idx and r[name_col_idx].strip()
    }

    rows_to_write = []
    skipped       = []
    for ex in NEW_EXERCISES:
        if ex['exercise_name'].lower() in existing_names:
            skipped.append(ex['exercise_name'])
            continue
        row = [ex.get(h, '') for h in headers]
        rows_to_write.append((ex['exercise_name'], row))

    if skipped:
        print(f'  Skipped (already exist): {skipped}')

    if not rows_to_write:
        print('  Nothing new to add.')
        return

    # Use explicit row numbers instead of append_row to avoid the Google Sheets
    # API OVERWRITE mode bug where successive appends land on the same row.
    next_row = len(all_rows) + 1
    print(f'  Writing {len(rows_to_write)} exercise(s) starting at row {next_row}...')

    for name, row in rows_to_write:
        ws.update(f'A{next_row}', [row], value_input_option='USER_ENTERED')
        print(f'  + Added: {name} (row {next_row})')
        next_row += 1

    print(f'  {len(rows_to_write)} exercise(s) added to Exercises_Library.')


# ── Part 2: Fix exercise names in Plans_Steps ─────────────────────────────────

def fix_plans_steps(spreadsheet):
    ws         = spreadsheet.worksheet('Plans_Steps')
    all_values = ws.get_all_values()
    headers    = all_values[0]

    try:
        ex_col_idx = headers.index('exercise_name')  # 0-based
    except ValueError:
        print('  ERROR: exercise_name column not found in Plans_Steps')
        return

    ex_col_letter = col_letter(ex_col_idx + 1)  # 1-based for A1 notation

    updates = []
    for row_num, row in enumerate(all_values[1:], start=2):   # row 1 = header
        current = row[ex_col_idx] if ex_col_idx < len(row) else ''
        if current in RENAMES:
            new_name = RENAMES[current]
            updates.append({
                'range':  f'{ex_col_letter}{row_num}',
                'values': [[new_name]],
            })
            print(f'  Row {row_num}: "{current}" -> "{new_name}"')

    if not updates:
        print('  Nothing to rename.')
        return

    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f'  {len(updates)} cell(s) updated in Plans_Steps.')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('Connecting to Google Sheets...')
    spreadsheet = _connect()
    print('Connected.\n')

    print('=== Part 1: Adding Category B exercises to Exercises_Library ===')
    add_library_exercises(spreadsheet)
    print()

    print('=== Part 2: Fixing Category A names in Plans_Steps ===')
    fix_plans_steps(spreadsheet)
    print()

    print('Done.')


if __name__ == '__main__':
    main()
