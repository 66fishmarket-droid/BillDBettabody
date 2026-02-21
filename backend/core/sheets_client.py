"""
Bill D'Bettabody - Google Sheets Direct Reader

Bypasses Make.com for read-only data that doesn't need automation logic.
Used for:
  - Exercise Bests (read into Bill's context + dashboard display)
  - Dashboard data (next session + relevant PBs for home screen)

Make.com is still used for ALL WRITE operations (Exercise Bests V2 scenario,
user upsert, training block generation, etc.). This module is READ ONLY.

Auth: Google Service Account via GOOGLE_SERVICE_ACCOUNT_JSON env var.
      Sheet shared with: github-actions-sheets-reader@bill-dbettabody-automation.iam.gserviceaccount.com

Column header names used here must match row 1 of each Google Sheet exactly.
If a field returns empty/wrong, check the actual sheet header spelling first.
"""

import os
import json
import logging
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# Read-only scope is all we need
_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Sheet tab names — update here if any sheet is renamed
SHEET_NAMES = {
    'exercise_bests':  'Exercise_Bests',
    'plans_sessions':  'Plans_Sessions',
    'plans_steps':     'Plans_Steps',
    'exercise_library': 'Exercise_Library',
    'plans_blocks':     'Plans_Blocks',
}

# Module-level cached connection (one auth per process)
_spreadsheet = None


# ============================================================
# CONNECTION
# ============================================================

def _get_spreadsheet():
    """
    Return authenticated Spreadsheet object, creating connection if needed.
    Caches at module level — one connection per server process.
    """
    global _spreadsheet

    if _spreadsheet is not None:
        return _spreadsheet

    sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID')

    if not sa_json:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set. "
            "Add service account JSON to .env or Railway environment variables."
        )
    if not spreadsheet_id:
        raise RuntimeError(
            "GOOGLE_SHEETS_SPREADSHEET_ID not set. "
            "Add the spreadsheet ID to .env or Railway environment variables."
        )

    try:
        sa_info = json.loads(sa_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}. "
            "Check it is single-line and wrapped in single quotes in .env."
        )

    try:
        creds = Credentials.from_service_account_info(sa_info, scopes=_SCOPES)
        client = gspread.authorize(creds)
        _spreadsheet = client.open_by_key(spreadsheet_id)
        logger.info("[Sheets] Connected to Google Spreadsheet successfully")
        return _spreadsheet
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Google Sheets: {e}")


def _get_worksheet(sheet_name):
    """Get a specific worksheet tab by name, with clear error on missing tab."""
    spreadsheet = _get_spreadsheet()
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        raise RuntimeError(
            f"Sheet tab '{sheet_name}' not found in spreadsheet. "
            "Check SHEET_NAMES dict in sheets_client.py matches actual tab names."
        )


def reset_connection():
    """
    Force a reconnect on the next call. Use this if the connection goes stale
    or credentials are rotated. Call from server startup or health check if needed.
    """
    global _spreadsheet
    _spreadsheet = None
    logger.info("[Sheets] Connection reset — will reconnect on next call")


# ============================================================
# EXERCISE BESTS
# ============================================================

def get_exercise_bests(client_id):
    """
    Read all Exercise Bests for a client directly from Google Sheets.

    Replaces the Make.com fetch in Load Client Context (modules 28-29).
    Returns data in named-key format so context_loader._format_exercise_bests()
    works without modification.

    Actual Exercise_Bests sheet headers (row 1):
      client_id, exercise_name, metric_key, metric_family, better_direction,
      context_key, current_value, current_unit, current_timestamp,
      current_evidence_type, current_evidence_ref, current_confidence,
      first_value, first_unit, first_timestamp, first_evidence_type,
      first_evidence_ref, strength_load_kg, strength_reps, strength_e1rm_kg,
      distance_m, duration_s, avg_power_w, avg_hr_bpm, notes,
      session_count, last_session_timestamp

    Args:
        client_id (str): Client identifier e.g. 'cli_matty'

    Returns:
        list[dict]: Exercise best records for this client.
                    Empty list if client has no records or on read error.
    """
    try:
        ws = _get_worksheet(SHEET_NAMES['exercise_bests'])
        rows = ws.get_all_records()

        # Filter by client_id (case-insensitive to be safe)
        client_id_lower = str(client_id).lower()
        client_rows = [
            r for r in rows
            if str(r.get('client_id', '')).lower() == client_id_lower
        ]

        logger.info(
            f"[Sheets] Exercise Bests: {len(client_rows)} records for {client_id} "
            f"(sheet total: {len(rows)} rows)"
        )
        return client_rows

    except RuntimeError:
        raise  # Propagate config/connection errors so caller knows something is wrong
    except Exception as e:
        logger.error(f"[Sheets] Error reading Exercise Bests for {client_id}: {e}")
        return []


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _get_progress_group(lib_entry):
    """
    Map an Exercise_Library row to a broad progress group name.
    Uses body_region + movement_pattern + category + metric_family.
    """
    if not lib_entry:
        return 'Other'

    body_region    = str(lib_entry.get('body_region', '')         or '').strip().lower()
    movement       = str(lib_entry.get('movement_pattern', '')    or '').strip().lower()
    category       = str(lib_entry.get('category', '')            or '').strip().lower()
    metric_family  = str(lib_entry.get('metric_family_default','') or '').strip().lower()
    training_focus = str(lib_entry.get('training_focus', '')      or '').strip().lower()

    # Cardio: distance vs endurance
    if category in ('cardio', 'conditioning'):
        if 'distance' in metric_family:
            return 'Distance'
        return 'Endurance'
    if 'distance' in metric_family:
        return 'Distance'

    # Upper body: push vs pull
    if body_region == 'upper':
        push_patterns = ('push', 'press', 'fly', 'dip', 'extension')
        pull_patterns = ('pull', 'row', 'curl', 'chin')
        if any(p in movement for p in push_patterns):
            return 'Upper Push'
        if any(p in movement for p in pull_patterns):
            return 'Upper Pull'
        return 'Upper Body'

    if body_region == 'lower':
        return 'Lower Body'

    if body_region in ('core', 'full_body', 'full body', 'total_body', 'total body'):
        return 'Full Body & Core'

    if 'endurance' in training_focus:
        return 'Endurance'

    return 'Other'


_GROUP_ORDER = [
    'Upper Push', 'Upper Pull', 'Lower Body',
    'Full Body & Core', 'Distance', 'Endurance',
    'Upper Body', 'Other',
]


# ============================================================
# DASHBOARD DATA
# ============================================================

def get_dashboard_data(client_id):
    """
    Fetch everything the frontend home screen needs in a single call.

    Does 3 direct sheet reads:
      1. Plans_Sessions  → find next upcoming session
      2. Plans_Steps     → exercises in that session (main segment only)
      3. Exercise_Bests  → PBs for those exercises + recent PBs (last 7 days)

    Expected Plans_Sessions headers (relevant columns):
      client_id, session_id, session_date, day_of_week, focus,
      session_summary, location, estimated_duration_minutes,
      phase_name, week_number, block_id, status

    Expected Plans_Steps headers (relevant columns):
      session_id, step_order, segment_type, exercise_name,
      sets, reps, load_kg

    Args:
        client_id (str): Client identifier

    Returns:
        dict with keys:
          next_session          (dict | None)  — session card data
          session_exercise_bests (list[dict])  — PBs for exercises in next session
          recent_pbs            (list[dict])   — PBs achieved in last 7 days
          block_summary         (dict | None)  — phase/week info for progress card

        Returns safe empty structure on any non-fatal error so the
        frontend can render gracefully with whatever is available.
    """
    result = {
        "next_session": None,
        "session_exercise_bests": [],
        "recent_pbs": [],
        "block_summary": None,
        "nutrition_targets": {},
        "supplement_protocol": [],
    }

    try:
        today_str = datetime.utcnow().strftime('%Y-%m-%d')

        # ----------------------------------------------------------
        # 1. Find the next upcoming session
        # ----------------------------------------------------------
        sessions_ws = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()

        client_id_lower = str(client_id).lower()
        terminal_statuses = {'completed', 'skipped', 'cancelled'}

        upcoming = [
            s for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
            and str(s.get('status', '')).lower() not in terminal_statuses
            and str(s.get('session_date', '')) >= today_str
        ]

        if not upcoming:
            logger.info(f"[Sheets] Dashboard: no upcoming sessions for {client_id}")
            return result

        # Sort ascending by date — first entry is the next session
        upcoming.sort(key=lambda s: str(s.get('session_date', '')))
        next_sess = upcoming[0]
        session_id = str(next_sess.get('session_id', ''))

        result['next_session'] = {
            'session_id':           session_id,
            'session_date':         next_sess.get('session_date', ''),
            'day_of_week':          next_sess.get('day_of_week', ''),
            'focus':                next_sess.get('focus', ''),
            'session_summary':      next_sess.get('session_summary', ''),
            'location':             next_sess.get('location', ''),
            'estimated_duration':   next_sess.get('estimated_duration_minutes', ''),
            'phase_name':           next_sess.get('phase_name', ''),
            'week_number':          next_sess.get('week_number', ''),
            'exercise_count':       0,  # filled in step 2
        }

        result['block_summary'] = {
            'phase_name':  next_sess.get('phase_name', ''),
            'week_number': next_sess.get('week_number', ''),
            'block_id':    next_sess.get('block_id', ''),
        }

        # ----------------------------------------------------------
        # 2. Get main-body exercises from that session
        # ----------------------------------------------------------
        session_exercise_names = []

        if session_id:
            steps_ws = _get_worksheet(SHEET_NAMES['plans_steps'])
            all_steps = steps_ws.get_all_records()

            session_steps = [
                s for s in all_steps
                if str(s.get('session_id', '')) == session_id
            ]

            # Count all steps for the session card
            result['next_session']['exercise_count'] = len(session_steps)

            # Only pull PBs for main-body exercises (not warmup/cooldown)
            main_steps = [
                s for s in session_steps
                if str(s.get('segment_type', '')).lower() == 'main'
            ]

            # Deduplicate exercise names (preserve order)
            seen = set()
            for step in main_steps:
                name = step.get('exercise_name', '')
                if name and name not in seen:
                    session_exercise_names.append(name)
                    seen.add(name)

        # ----------------------------------------------------------
        # 3. Exercise Bests — session-relevant + recent
        # ----------------------------------------------------------
        all_bests = get_exercise_bests(client_id)

        # PBs for exercises appearing in the upcoming session
        if session_exercise_names:
            result['session_exercise_bests'] = [
                b for b in all_bests
                if b.get('exercise_name', '') in session_exercise_names
            ]

        # PBs set in the last 7 days (regardless of upcoming session)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        result['recent_pbs'] = [
            b for b in all_bests
            if str(b.get('current_timestamp', ''))[:10] >= seven_days_ago
        ]

        # ----------------------------------------------------------
        # 4. Block nutrition targets + supplement protocol
        #    from Plans_Blocks — keyed by block_id from the next session.
        #    Non-fatal: dashboard renders without these if lookup fails.
        # ----------------------------------------------------------
        block_id = str(next_sess.get('block_id', '')).strip()
        if block_id:
            try:
                blocks_ws  = _get_worksheet(SHEET_NAMES['plans_blocks'])
                all_blocks = blocks_ws.get_all_records()

                block = next(
                    (b for b in all_blocks if str(b.get('block_id', '')) == block_id),
                    None
                )

                if block:
                    # nutrition_targets: stored as JSON object string
                    nt_raw = str(block.get('nutrition_targets', '') or '').strip()
                    if nt_raw:
                        try:
                            result['nutrition_targets'] = json.loads(nt_raw)
                        except Exception:
                            logger.warning(
                                f"[Sheets] Could not parse nutrition_targets for block {block_id}"
                            )

                    # supplement_protocol: stored as comma-separated JSON objects
                    # e.g. {"name":"Creatine","dosage":"5g","timing":"daily"}, {...}
                    sp_raw = str(block.get('supplement_protocol', '') or '').strip()
                    if sp_raw:
                        try:
                            if not sp_raw.startswith('['):
                                sp_raw = '[' + sp_raw + ']'
                            result['supplement_protocol'] = json.loads(sp_raw)
                        except Exception:
                            logger.warning(
                                f"[Sheets] Could not parse supplement_protocol for block {block_id}"
                            )

                    logger.info(
                        f"[Sheets] Block {block_id}: "
                        f"nutrition_targets={bool(result['nutrition_targets'])}, "
                        f"supplements={len(result['supplement_protocol'])}"
                    )
            except Exception as e:
                logger.warning(f"[Sheets] Plans_Blocks lookup failed (non-fatal): {e}")

        logger.info(
            f"[Sheets] Dashboard for {client_id}: "
            f"next_session={result['next_session']['session_date']}, "
            f"session_bests={len(result['session_exercise_bests'])}, "
            f"recent_pbs={len(result['recent_pbs'])}"
        )

        return result

    except RuntimeError:
        raise  # Config/connection errors should surface, not be swallowed
    except Exception as e:
        logger.error(f"[Sheets] Error building dashboard for {client_id}: {e}")
        return result  # Return whatever was built before the error


# ============================================================
# SESSION DETAIL
# ============================================================

def get_session_detail(client_id, session_id):
    """
    Fetch full session detail: session metadata, steps, and relevant PBs.

    Args:
        client_id (str): Client identifier
        session_id (str): Session identifier

    Returns:
        dict: {
          "session": { ... } | None,
          "steps": [ ... ],
          "exercise_bests": [ ... ]
        }
    """
    result = {
        "session": None,
        "steps": [],
        "exercise_bests": [],
    }

    try:
        if not client_id or not session_id:
            return result

        # ----------------------------------------------------------
        # 1. Session metadata
        # ----------------------------------------------------------
        sessions_ws = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()

        client_id_lower = str(client_id).lower()
        session_id_str = str(session_id)

        matched = [
            s for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
            and str(s.get('session_id', '')) == session_id_str
        ]

        if not matched:
            logger.info(f"[Sheets] Session not found: {session_id} for {client_id}")
            return result

        sess = matched[0]
        result["session"] = {
            "session_id": sess.get('session_id', ''),
            "session_date": sess.get('session_date', ''),
            "day_of_week": sess.get('day_of_week', ''),
            "focus": sess.get('focus', ''),
            "session_summary": sess.get('session_summary', ''),
            "location": sess.get('location', ''),
            "estimated_duration_minutes": sess.get('estimated_duration_minutes', ''),
            "phase_name": sess.get('phase_name', ''),
            "week_number": sess.get('week_number', ''),
            "block_id": sess.get('block_id', ''),
            "intended_intensity_rpe": sess.get('intended_intensity_rpe', ''),
        }

        # ----------------------------------------------------------
        # 2. Steps for the session
        # ----------------------------------------------------------
        steps_ws = _get_worksheet(SHEET_NAMES['plans_steps'])
        all_steps = steps_ws.get_all_records()

        session_steps = [
            s for s in all_steps
            if str(s.get('session_id', '')) == session_id_str
        ]

        # Sort by step_order if present
        def _step_order(row):
            try:
                return int(row.get('step_order', 0))
            except Exception:
                return 0

        session_steps.sort(key=_step_order)
        result["steps"] = session_steps

        # ----------------------------------------------------------
        # 3. Join Exercise_Library fields onto each step
        # Fields attached: video_url, exercise_description_long,
        #   coaching_cues_short, equipment, safety_notes,
        #   common_mistakes, regression, progression
        # Join key: exercise_name (case-insensitive)
        # Non-fatal — step cards still render without library data.
        # ----------------------------------------------------------
        _LIB_FIELDS = (
            'video_url', 'exercise_description_short', 'exercise_description_long',
            'coaching_cues_short', 'equipment', 'safety_notes', 'common_mistakes',
            'regression', 'progression',
        )

        if session_steps:
            try:
                lib_ws = _get_worksheet(SHEET_NAMES['exercise_library'])
                lib_rows = lib_ws.get_all_records()

                # Build lookup: lowercase exercise_name → first matching row
                lib_lookup = {}
                for row in lib_rows:
                    name = str(row.get('exercise_name', '')).strip().lower()
                    if name and name not in lib_lookup:
                        lib_lookup[name] = row

                joined = 0
                for step in session_steps:
                    key = str(step.get('exercise_name', '')).strip().lower()
                    lib_entry = lib_lookup.get(key)
                    if lib_entry:
                        for field in _LIB_FIELDS:
                            # Only fill if not already set on the step
                            if not step.get(field):
                                step[field] = lib_entry.get(field, '')
                        joined += 1

                logger.info(
                    f"[Sheets] Exercise_Library joined: {joined}/{len(session_steps)} steps matched"
                )
            except Exception as e:
                logger.warning(f"[Sheets] Exercise_Library join failed (non-fatal): {e}")

        # ----------------------------------------------------------
        # 4. Exercise bests relevant to this session
        # ----------------------------------------------------------
        exercise_names = []
        seen = set()
        for step in session_steps:
            name = step.get('exercise_name', '')
            if name and name not in seen:
                exercise_names.append(name)
                seen.add(name)

        if exercise_names:
            all_bests = get_exercise_bests(client_id)
            result["exercise_bests"] = [
                b for b in all_bests
                if b.get('exercise_name', '') in exercise_names
            ]

        logger.info(
            f"[Sheets] Session detail for {client_id} {session_id}: "
            f"steps={len(result['steps'])}, bests={len(result['exercise_bests'])}"
        )

        return result

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[Sheets] Error building session detail for {client_id}, {session_id}: {e}")
        return result


# ============================================================
# PROGRESS DATA
# ============================================================

def get_progress_data(client_id):
    """
    Build grouped progress data for the progress/history screen.

    Four sheet reads:
      1. Exercise_Bests  → first_value (started) + current_value (best ever)
      2. Exercise_Library → grouping metadata (body_region, movement_pattern, etc.)
      3. Plans_Sessions  → completed session IDs for this client
      4. Plans_Steps     → most recent actual_top_set_value per exercise

    Groups exercises into broad training categories, calculates % improvement
    from first to best, and returns most recent performance separately.

    Returns:
        dict: {
          "groups": [
            {
              "name": str,
              "avg_improvement_pct": float | None,
              "exercise_count": int,
              "exercises": [
                {
                  "exercise_name": str,
                  "metric_key": str,
                  "unit": str,
                  "first_value": float | None,
                  "best_value": float | None,
                  "recent_value": float | None,
                  "improvement_pct": float | None,
                  "session_count": int | str,
                  "better_direction": str
                }, ...
              ]
            }, ...
          ]
        }
    """
    result = {"groups": []}

    try:
        if not client_id:
            return result

        client_id_lower = str(client_id).lower()

        # ----------------------------------------------------------
        # 1. Exercise Bests — first and best values
        # ----------------------------------------------------------
        bests = get_exercise_bests(client_id)
        if not bests:
            return result

        bests_by_name = {b['exercise_name']: b for b in bests}

        # ----------------------------------------------------------
        # 2. Exercise Library — grouping metadata
        # ----------------------------------------------------------
        lib_ws   = _get_worksheet(SHEET_NAMES['exercise_library'])
        lib_rows = lib_ws.get_all_records()
        lib_lookup = {}
        for row in lib_rows:
            name = str(row.get('exercise_name', '') or '').strip().lower()
            if name and name not in lib_lookup:
                lib_lookup[name] = row

        # ----------------------------------------------------------
        # 3. Plans_Sessions — completed session IDs for this client
        # ----------------------------------------------------------
        sessions_ws = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()
        completed_ids = {
            str(s.get('session_id', ''))
            for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
            and str(s.get('status', '')).lower() == 'completed'
        }

        # ----------------------------------------------------------
        # 4. Plans_Steps — most recent actual_top_set_value per exercise
        # ----------------------------------------------------------
        recent_by_exercise = {}  # exercise_name → {value, completed_timestamp}

        if completed_ids:
            steps_ws  = _get_worksheet(SHEET_NAMES['plans_steps'])
            all_steps = steps_ws.get_all_records()

            for step in all_steps:
                if str(step.get('session_id', '')) not in completed_ids:
                    continue
                exercise  = str(step.get('exercise_name', '') or '').strip()
                top_val   = step.get('actual_top_set_value', '')
                ts        = str(step.get('completed_timestamp', '') or '')
                if not exercise or not top_val or not ts:
                    continue

                existing = recent_by_exercise.get(exercise)
                if not existing or ts > existing['completed_timestamp']:
                    recent_by_exercise[exercise] = {
                        'value': top_val,
                        'completed_timestamp': ts,
                    }

        # ----------------------------------------------------------
        # 5. Assemble exercise records and group them
        # ----------------------------------------------------------
        def _improvement_pct(first_val, best_val, better_direction):
            f = _safe_float(first_val)
            b = _safe_float(best_val)
            if f is None or b is None or f == 0:
                return None
            if str(better_direction).lower() == 'lower':
                return round(((f - b) / abs(f)) * 100, 1)
            return round(((b - f) / abs(f)) * 100, 1)

        groups_dict = {}

        for exercise_name, best in bests_by_name.items():
            first_val  = best.get('first_value', '')
            best_val   = best.get('current_value', '')
            if not first_val or not best_val:
                continue

            better_dir   = str(best.get('better_direction', 'higher') or 'higher')
            improvement  = _improvement_pct(first_val, best_val, better_dir)
            lib_entry    = lib_lookup.get(exercise_name.strip().lower())
            group        = _get_progress_group(lib_entry)
            recent       = recent_by_exercise.get(exercise_name, {})

            record = {
                'exercise_name':    exercise_name,
                'metric_key':       best.get('metric_key', ''),
                'unit':             best.get('current_unit', ''),
                'first_value':      _safe_float(first_val),
                'best_value':       _safe_float(best_val),
                'recent_value':     _safe_float(recent.get('value')) if recent else None,
                'improvement_pct':  improvement,
                'session_count':    best.get('session_count', ''),
                'better_direction': better_dir,
            }

            groups_dict.setdefault(group, []).append(record)

        # ----------------------------------------------------------
        # 6. Sort, average, and order groups
        # ----------------------------------------------------------
        groups = []

        for group_name in _GROUP_ORDER:
            exercises = groups_dict.pop(group_name, [])
            if not exercises:
                continue

            exercises.sort(
                key=lambda x: x.get('improvement_pct') or 0,
                reverse=True
            )

            pcts    = [e['improvement_pct'] for e in exercises if e['improvement_pct'] is not None]
            avg_pct = round(sum(pcts) / len(pcts), 1) if pcts else None

            groups.append({
                'name':                group_name,
                'avg_improvement_pct': avg_pct,
                'exercise_count':      len(exercises),
                'exercises':           exercises,
            })

        # Any remaining groups not in _GROUP_ORDER
        for group_name, exercises in groups_dict.items():
            exercises.sort(key=lambda x: x.get('improvement_pct') or 0, reverse=True)
            pcts    = [e['improvement_pct'] for e in exercises if e['improvement_pct'] is not None]
            avg_pct = round(sum(pcts) / len(pcts), 1) if pcts else None
            groups.append({
                'name':                group_name,
                'avg_improvement_pct': avg_pct,
                'exercise_count':      len(exercises),
                'exercises':           exercises,
            })

        result['groups'] = groups

        logger.info(
            f"[Sheets] Progress for {client_id}: "
            f"{len(groups)} groups, "
            f"{sum(g['exercise_count'] for g in groups)} exercises"
        )

        return result

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[Sheets] Error building progress data for {client_id}: {e}")
        return result
