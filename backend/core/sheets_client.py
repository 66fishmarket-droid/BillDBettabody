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
import re
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
    'exercise_bests':     'Exercise_Bests',
    'plans_sessions':     'Plans_Sessions',
    'plans_steps':        'Plans_Steps',
    'exercise_library':   'Exercises_Library',
    'plans_blocks':       'Plans_Blocks',
    'metric_definitions': 'Metric_Definitions',
    'exercise_metric_map':'Exercise_Metric_Map',
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


def _week_number_from_id(week_id):
    """Extract the rightmost number from a week_id string.
    e.g. 'blk_001_w3' → 3,  'week_4' → 4,  'w12' → 12
    Returns None if no number found.
    """
    nums = re.findall(r'\d+', str(week_id or ''))
    return int(nums[-1]) if nums else None


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

def get_dashboard_data(client_id, _retry=True):
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
        "completed_sessions": 0,
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

        # Count completed sessions for this client
        result['completed_sessions'] = sum(
            1 for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
            and _effective_session_status(s) == 'completed'
        )

        upcoming = [
            s for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
            and _effective_session_status(s) not in terminal_statuses
            and str(s.get('session_date', '')) >= today_str
        ]

        if not upcoming:
            logger.info(f"[Sheets] Dashboard: no upcoming sessions for {client_id}")
            return result

        # Sort ascending by date — first entry is the next session
        upcoming.sort(key=lambda s: str(s.get('session_date', '')))
        next_sess = upcoming[0]
        session_id = str(next_sess.get('session_id', ''))

        week_id     = str(next_sess.get('week_id', '') or '').strip()
        week_number = _week_number_from_id(week_id)
        phase_name  = str(next_sess.get('phase', '') or '').strip()

        result['next_session'] = {
            'session_id':           session_id,
            'session_date':         next_sess.get('session_date', ''),
            'day_of_week':          next_sess.get('day_of_week', ''),
            'focus':                next_sess.get('focus', ''),
            'session_summary':      next_sess.get('session_summary', ''),
            'location':             next_sess.get('location', ''),
            'estimated_duration':   next_sess.get('estimated_duration_minutes', ''),
            'phase_name':           phase_name,
            'week_number':          week_number,
            'exercise_count':       0,  # filled in step 2
        }

        result['block_summary'] = {
            'phase_name':  phase_name,
            'week_number': week_number,
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

            result['next_session']['exercise_names'] = session_exercise_names

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
        if _retry and _is_connection_error(e):
            logger.warning(f"[Sheets] Connection reset in get_dashboard_data — reconnecting and retrying")
            reset_connection()
            return get_dashboard_data(client_id, _retry=False)
        logger.error(f"[Sheets] Error building dashboard for {client_id}: {e}")
        return result  # Return whatever was built before the error


# ============================================================
# WEEK VIEW
# ============================================================

def _effective_session_status(s):
    """
    Return the current effective status of a Plans_Sessions row.

    Plans_Sessions has two status-related columns:
      - 'status'          written by Make.com at plan creation (e.g. 'scheduled')
      - 'session_status'  written by Python (sheets_writer) on completion/skip

    session_status reflects the latest actual state, so it takes priority.
    Fall back to 'status' if session_status is empty (not yet acted on).
    """
    ss = str(s.get('session_status', '') or '').strip().lower()
    return ss if ss else str(s.get('status', '') or '').strip().lower()


def _is_connection_error(exc):
    """Return True if the exception is a transient network/connection error."""
    msg = str(exc).lower()
    return any(k in msg for k in (
        'connectionreseterror', 'connection aborted', 'connection reset',
        'connectionabortederror', 'remotedisconnected', 'broken pipe',
    ))


def get_week_sessions(client_id, _retry=True):
    """
    Return all sessions for the client's current training week.

    "Current week" = the week_id of the next upcoming session.
    Falls back to the next 7 calendar days if no week_id is found.

    Each session includes its main-body exercise names from Plans_Steps.

    Returns:
        dict with keys:
          week_id       (str | None)
          week_number   (int | None)
          phase_name    (str | None)
          sessions      (list[dict]) — ordered by day number / date
    """
    result = {
        "week_id": None,
        "week_number": None,
        "phase_name": None,
        "sessions": [],
    }

    try:
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        client_id_lower = str(client_id).lower()
        terminal_statuses = {'completed', 'skipped', 'cancelled'}

        sessions_ws = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()

        client_sessions = [
            s for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
        ]

        # Find the next upcoming session to anchor the week
        upcoming = [
            s for s in client_sessions
            if _effective_session_status(s) not in terminal_statuses
            and str(s.get('session_date', '')) >= today_str
        ]
        upcoming.sort(key=lambda s: str(s.get('session_date', '')))

        if not upcoming:
            return result

        anchor = upcoming[0]
        week_id = str(anchor.get('week_id', '') or '').strip()

        # All sessions in the same week
        if week_id:
            week_sessions = [
                s for s in client_sessions
                if str(s.get('week_id', '') or '') == week_id
            ]
        else:
            # Fallback: sessions within 7 days of today
            cutoff = (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
            week_sessions = [
                s for s in client_sessions
                if today_str <= str(s.get('session_date', '')) <= cutoff
            ]

        week_sessions.sort(key=lambda s: (str(s.get('session_date', '')), int(s.get('day', 0) or 0)))

        result['week_id']     = week_id or None
        result['week_number'] = _week_number_from_id(week_id)
        result['phase_name']  = str(anchor.get('phase', '') or '').strip() or None

        # Load step exercise names for each session in the week
        steps_ws  = _get_worksheet(SHEET_NAMES['plans_steps'])
        all_steps = steps_ws.get_all_records()

        steps_by_session = {}
        for step in all_steps:
            sid = str(step.get('session_id', '') or '')
            if sid:
                steps_by_session.setdefault(sid, []).append(step)

        for s in week_sessions:
            sid      = str(s.get('session_id', '') or '')
            steps    = steps_by_session.get(sid, [])
            main_ex  = [
                step.get('exercise_name', '')
                for step in sorted(steps, key=lambda t: int(t.get('step_order', 0) or 0))
                if str(step.get('segment_type', '')).lower() == 'main'
                and step.get('exercise_name')
            ]

            result['sessions'].append({
                'session_id':               sid,
                'session_date':             str(s.get('session_date', '') or ''),
                'day_of_week':              str(s.get('day_of_week', '') or ''),
                'focus':                    str(s.get('focus', '') or ''),
                'location':                 str(s.get('location', '') or ''),
                'estimated_duration':       s.get('estimated_duration_minutes', ''),
                'intended_intensity_rpe':   s.get('intended_intensity_rpe', ''),
                'status':                   _effective_session_status(s),
                'session_summary':          str(s.get('session_summary', '') or ''),
                'exercises':                main_ex,
            })

        logger.info(
            f"[Sheets] Week view for {client_id}: "
            f"week_id={week_id}, {len(result['sessions'])} sessions"
        )
        return result

    except RuntimeError:
        raise
    except Exception as e:
        if _retry and _is_connection_error(e):
            logger.warning(f"[Sheets] Connection reset in get_week_sessions — reconnecting and retrying")
            reset_connection()
            return get_week_sessions(client_id, _retry=False)
        logger.error(f"[Sheets] Error building week view for {client_id}: {e}")
        return result


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
            'regression', 'progression', 'metric_family_default', 'special_flags',
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

                lib_names = list(lib_lookup.keys())  # for fuzzy fallback

                def _fuzzy_lib_match(step_key):
                    """
                    Fallback when exact match fails.
                    1. Check if any library name *contains* the step name as a whole word
                       e.g. step="romanian deadlift" matches "romanian deadlift (barbell)"
                    2. Check if the step name *contains* a library name as a whole word
                       e.g. step="barbell deadlift" matches "deadlift (barbell)"
                    Returns the best matching library row or None.
                    """
                    if not step_key:
                        return None
                    # Strategy 1: step_key is a substring of a library name
                    candidates = [n for n in lib_names if step_key in n]
                    if len(candidates) == 1:
                        return lib_lookup[candidates[0]]
                    # Strategy 2: a library name is a substring of step_key
                    candidates = [n for n in lib_names if n in step_key]
                    if len(candidates) == 1:
                        return lib_lookup[candidates[0]]
                    # Multiple or zero candidates — too ambiguous, skip
                    return None

                joined = 0
                fuzzy_joined = 0
                for step in session_steps:
                    key = str(step.get('exercise_name', '')).strip().lower()
                    lib_entry = lib_lookup.get(key)
                    if not lib_entry:
                        lib_entry = _fuzzy_lib_match(key)
                        if lib_entry:
                            fuzzy_joined += 1
                    if lib_entry:
                        for field in _LIB_FIELDS:
                            # Only fill if not already set on the step
                            if not step.get(field):
                                step[field] = lib_entry.get(field, '')
                        # Parse multi-URL video_url (newline-separated in Google Sheets)
                        raw_urls = step.get('video_url', '') or ''
                        video_urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]
                        step['video_urls'] = video_urls
                        if video_urls:
                            step['video_url'] = video_urls[0]  # first URL for backward compat
                        joined += 1

                logger.info(
                    f"[Sheets] Exercise_Library joined: {joined}/{len(session_steps)} steps matched "
                    f"({fuzzy_joined} via fuzzy)"
                )
            except Exception as e:
                logger.warning(f"[Sheets] Exercise_Library join failed (non-fatal): {e}")

        # ----------------------------------------------------------
        # 3b. Metric_definitions + Exercise_Metric_Map joins
        #
        #  metric_key:         exercise_name → Exercise_Metric_Map (priority 1, enabled)
        #                      fallback: metric_family_default → Metric_definitions
        #                                (is_default_for_family = TRUE)
        #  metric_context_key: exercise_name → Exercise_Metric_Map.context_key
        #
        #  Both honour "only fill if not already set on the step" so that
        #  any value Make.com wrote to Plans_Steps is preserved.
        # ----------------------------------------------------------
        if session_steps:
            try:
                # Build metric_family → metric_key and metric_key → better_direction
                # from Metric_definitions in a single pass.
                family_to_metric_key      = {}
                metric_key_to_better_dir  = {}
                md_ws = _get_worksheet(SHEET_NAMES['metric_definitions'])
                for row in md_ws.get_all_records():
                    key    = str(row.get('metric_key',        '') or '').strip()
                    family = str(row.get('metric_family',     '') or '').strip().lower()
                    bdir   = str(row.get('better_direction',  '') or '').strip().lower() or 'higher'
                    if key:
                        metric_key_to_better_dir[key] = bdir
                    if str(row.get('is_default_for_family', '')).strip().upper() == 'TRUE':
                        if family and key and family not in family_to_metric_key:
                            family_to_metric_key[family] = key

                # Build exercise_name → {metric_key, context_key} from Exercise_Metric_Map
                # metric_key: always taken from priority=1 entry.
                # metric_context_key: only auto-assigned for exercises with a SINGLE
                #   enabled entry (strength exercises with one canonical context, e.g.
                #   squat_barbell). For exercises with multiple entries (cardio exercises
                #   with distance variants — running_5k, running_10k, etc.) we leave it
                #   blank so the explicitly-set value on Plans_Steps is preserved.
                #   Bill writes the correct context_key (e.g. "5k") when calling
                #   populate_training_week for a specific time-trial step. General
                #   steady-state cardio steps intentionally have no context_key.
                emm_ws  = _get_worksheet(SHEET_NAMES['exercise_metric_map'])
                emm_all = [r for r in emm_ws.get_all_records()
                           if str(r.get('enabled', '')).strip().upper() == 'TRUE']

                # Count enabled rows per exercise to detect multi-context exercises
                emm_counts = {}
                for row in emm_all:
                    n = str(row.get('exercise_name', '') or '').strip().lower()
                    if n:
                        emm_counts[n] = emm_counts.get(n, 0) + 1

                emm_rows = sorted(emm_all, key=lambda r: int(r.get('priority', 999) or 999))
                exercise_to_metric = {}
                for row in emm_rows:
                    name = str(row.get('exercise_name', '') or '').strip().lower()
                    if name and name not in exercise_to_metric:
                        multi_context = emm_counts.get(name, 1) > 1
                        exercise_to_metric[name] = {
                            'metric_key':        str(row.get('metric_key',  '') or '').strip(),
                            # Leave blank for multi-context (cardio) exercises
                            'metric_context_key': '' if multi_context else str(row.get('context_key', '') or '').strip(),
                        }

                # Apply to each step
                metric_joined = 0
                for step in session_steps:
                    ex_key   = str(step.get('exercise_name', '') or '').strip().lower()
                    emm_entry = exercise_to_metric.get(ex_key)

                    # metric_key: Exercise_Metric_Map first, then Metric_definitions fallback
                    if not step.get('metric_key'):
                        if emm_entry and emm_entry['metric_key']:
                            step['metric_key'] = emm_entry['metric_key']
                        else:
                            family = str(step.get('metric_family_default', '') or '').strip().lower()
                            if family and family in family_to_metric_key:
                                step['metric_key'] = family_to_metric_key[family]

                    # metric_context_key: Exercise_Metric_Map only
                    if not step.get('metric_context_key') and emm_entry:
                        step['metric_context_key'] = emm_entry['metric_context_key']

                    # better_direction: resolved from Metric_Definitions via metric_key
                    if not step.get('better_direction') and step.get('metric_key'):
                        step['better_direction'] = metric_key_to_better_dir.get(step['metric_key'], 'higher')

                    if step.get('metric_key'):
                        metric_joined += 1

                logger.info(
                    f"[Sheets] Metric join: {metric_joined}/{len(session_steps)} steps resolved"
                )

            except Exception as e:
                logger.warning(f"[Sheets] Metric join failed (non-fatal): {e}")

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
        lib_names = list(lib_lookup.keys())

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
            ex_key       = exercise_name.strip().lower()
            lib_entry    = lib_lookup.get(ex_key)
            if not lib_entry:
                # Fuzzy fallback: name is substring of one library entry, or vice versa
                candidates = [n for n in lib_names if ex_key in n]
                if len(candidates) == 1:
                    lib_entry = lib_lookup[candidates[0]]
                else:
                    candidates = [n for n in lib_names if n in ex_key]
                    if len(candidates) == 1:
                        lib_entry = lib_lookup[candidates[0]]
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


# ============================================================
# LIFETIME STATS
# ============================================================

def get_lifetime_stats(client_id):
    """
    Compute lifetime aggregate stats from Plans_Steps for completed sessions.

    Iterates all actual_setN_value / actual_setN_reps columns (1–10) for
    each step belonging to a completed session of this client.

    Returns:
        dict: {
          'sessions_completed': int,
          'total_sets': int,
          'total_reps': int,
          'total_volume_kg': int,   # sum of (weight_kg × reps) for kg sets
          'total_distance_m': int,  # sum of distance values converted to metres
        }
    """
    result = {
        'sessions_completed': 0,
        'total_sets': 0,
        'total_reps': 0,
        'total_volume_kg': 0,
        'total_distance_m': 0,
    }

    if not client_id:
        return result

    try:
        client_id_lower = str(client_id).lower()

        # Completed session IDs for this client
        sessions_ws = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()
        completed_ids = {
            str(s.get('session_id', ''))
            for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
            and _effective_session_status(s) == 'completed'
        }

        result['sessions_completed'] = len(completed_ids)

        if not completed_ids:
            return result

        steps_ws = _get_worksheet(SHEET_NAMES['plans_steps'])
        all_steps = steps_ws.get_all_records()

        volume_kg = 0.0
        distance_m = 0.0

        for step in all_steps:
            if str(step.get('session_id', '')) not in completed_ids:
                continue

            for n in range(1, 11):
                reps_raw   = step.get(f'actual_set{n}_reps', '')
                value_raw  = step.get(f'actual_set{n}_value', '')
                metric     = str(step.get(f'actual_set{n}_metric', '') or '').strip().lower()

                reps  = _safe_float(reps_raw)
                value = _safe_float(value_raw)

                if reps is None and value is None:
                    continue  # empty set slot

                result['total_sets'] += 1

                if reps is not None:
                    result['total_reps'] += int(reps)

                if value is not None:
                    if metric == 'kg':
                        volume_kg += value * (int(reps) if reps else 1)
                    elif metric in ('m', 'metres', 'meters'):
                        distance_m += value
                    elif metric == 'km':
                        distance_m += value * 1000

        result['total_volume_kg'] = round(volume_kg)
        result['total_distance_m'] = round(distance_m)

        logger.info(
            f"[Sheets] Lifetime stats for {client_id}: "
            f"sessions={result['sessions_completed']}, "
            f"sets={result['total_sets']}, reps={result['total_reps']}, "
            f"volume_kg={result['total_volume_kg']}, distance_m={result['total_distance_m']}"
        )

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[Sheets] Error computing lifetime stats for {client_id}: {e}")

    return result


# ============================================================
# WEEKLY PREP CHECK
# ============================================================

def get_clients_needing_weekly_prep():
    """
    Find (client_id, week_id) pairs where the next upcoming training week
    has sessions but no Plans_Steps rows yet — i.e. populate_training_week
    has not been called for that week.

    Called by the Sunday automation endpoint (/admin/weekly-prep) to determine
    which clients need their week auto-populated.

    Logic:
      1. Find all upcoming sessions (date >= tomorrow, non-terminal status)
      2. For each client, anchor on their earliest upcoming week_id
      3. Collect all session_ids in that week
      4. Check Plans_Steps for those session_ids
      5. Return clients where no steps exist yet

    Returns:
        list[dict]: Each item: {client_id, week_id, session_count}
                    Empty list if all clients are already set up.
    """
    try:
        # Look back 7 days so current-week sessions are included even when
        # running mid-week (e.g. manual trigger on Thursday for a Mon-started week).
        window_start = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        terminal = {'completed', 'skipped', 'cancelled'}

        sessions_ws = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()

        # Non-terminal sessions within the rolling window
        upcoming = [
            s for s in all_sessions
            if str(s.get('session_date', '')) >= window_start
            and _effective_session_status(s) not in terminal
        ]

        # For each client: find the earliest upcoming week_id, collect its session_ids
        # Sort ascending so the first session we hit per client is their nearest upcoming one
        upcoming.sort(key=lambda s: str(s.get('session_date', '')))

        client_week = {}  # client_id → {week_id: str, session_ids: list}
        for s in upcoming:
            client_id = str(s.get('client_id', '') or '').strip()
            week_id   = str(s.get('week_id',   '') or '').strip()
            session_id = str(s.get('session_id', '') or '').strip()
            if not client_id or not week_id or not session_id:
                continue
            if client_id not in client_week:
                # First (nearest) upcoming week for this client
                client_week[client_id] = {'week_id': week_id, 'session_ids': []}
            if client_week[client_id]['week_id'] == week_id:
                client_week[client_id]['session_ids'].append(session_id)

        if not client_week:
            logger.info("[Sheets] Weekly prep check: no upcoming sessions found")
            return []

        # Load all Plans_Steps session_ids in one pass
        steps_ws = _get_worksheet(SHEET_NAMES['plans_steps'])
        all_steps = steps_ws.get_all_records()
        sessions_with_steps = {
            str(s.get('session_id', ''))
            for s in all_steps
            if s.get('session_id')
        }

        needing_prep = []
        for client_id, info in client_week.items():
            week_id     = info['week_id']
            session_ids = info['session_ids']
            has_steps   = any(sid in sessions_with_steps for sid in session_ids)

            if has_steps:
                logger.info(
                    f"[Sheets] Weekly prep: {client_id} / {week_id} already has steps — skipping"
                )
            else:
                logger.info(
                    f"[Sheets] Weekly prep: {client_id} / {week_id} "
                    f"needs population ({len(session_ids)} sessions)"
                )
                needing_prep.append({
                    'client_id':     client_id,
                    'week_id':       week_id,
                    'session_count': len(session_ids),
                })

        return needing_prep

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[Sheets] Error in get_clients_needing_weekly_prep: {e}")
        raise


# ============================================================
# EXERCISE NAME AUDIT
# ============================================================

def audit_exercise_names(client_id=None):
    """
    Compare all exercise names in Plans_Steps against the Exercises_Library.

    For each unique exercise name finds in Plans_Steps, reports whether it
    matches the library exactly, matches via fuzzy fallback, or has no match.

    Used to identify exercises that were prescribed with non-canonical names
    (i.e. Bill invented the name rather than using exercise_filter output).

    Args:
        client_id (str | None): If provided, only audit steps for this client.
                                If None, audit ALL clients.

    Returns:
        dict: {
          "summary": {
            "total_unique_names": int,
            "exact_matches": int,
            "fuzzy_matches": int,
            "no_matches": int,
          },
          "exact": [{"exercise_name": str, "session_ids": [...]}],
          "fuzzy": [{"exercise_name": str, "matched_library_name": str, "session_ids": [...]}],
          "unmatched": [{"exercise_name": str, "session_ids": [...], "client_ids": [...]}],
          "library_names": [str, ...]  — full list of canonical names for reference
        }
    """
    result = {
        "summary": {
            "total_unique_names": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "no_matches": 0,
        },
        "exact": [],
        "fuzzy": [],
        "unmatched": [],
        "library_names": [],
    }

    # ── 1. Load Exercises_Library ────────────────────────────
    lib_ws   = _get_worksheet(SHEET_NAMES['exercise_library'])
    lib_rows = lib_ws.get_all_records()

    lib_lookup = {}
    for row in lib_rows:
        name = str(row.get('exercise_name', '') or '').strip().lower()
        if name and name not in lib_lookup:
            lib_lookup[name] = row

    lib_names = list(lib_lookup.keys())
    result["library_names"] = sorted(
        str(row.get('exercise_name', '')) for row in lib_rows
        if row.get('exercise_name')
    )

    # ── 2. Load Plans_Steps (optionally filtered by client) ──
    steps_ws  = _get_worksheet(SHEET_NAMES['plans_steps'])
    all_steps = steps_ws.get_all_records()

    if client_id:
        # Plans_Steps doesn't store client_id directly — join via session_id
        sessions_ws  = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()
        client_id_lower = str(client_id).lower()
        client_session_ids = {
            str(s.get('session_id', ''))
            for s in all_sessions
            if str(s.get('client_id', '')).lower() == client_id_lower
        }
        steps = [s for s in all_steps if str(s.get('session_id', '')) in client_session_ids]
    else:
        # Need client info per session for the report
        sessions_ws  = _get_worksheet(SHEET_NAMES['plans_sessions'])
        all_sessions = sessions_ws.get_all_records()
        session_to_client = {
            str(s.get('session_id', '')): str(s.get('client_id', ''))
            for s in all_sessions
        }
        steps = all_steps

    # ── 3. Collect unique names with session context ─────────
    # name_lower → {"display_name": str, "session_ids": set, "client_ids": set}
    name_registry = {}

    for step in steps:
        raw_name = str(step.get('exercise_name', '') or '').strip()
        if not raw_name:
            continue
        key = raw_name.lower()
        if key not in name_registry:
            name_registry[key] = {
                "display_name": raw_name,
                "session_ids": set(),
                "client_ids": set(),
            }
        sid = str(step.get('session_id', '') or '')
        if sid:
            name_registry[key]["session_ids"].add(sid)
            if client_id is None:
                cid = session_to_client.get(sid, '')
                if cid:
                    name_registry[key]["client_ids"].add(cid)

    # ── 4. Classify each name ────────────────────────────────
    for key, info in sorted(name_registry.items()):
        display     = info["display_name"]
        session_ids = sorted(info["session_ids"])
        client_ids  = sorted(info["client_ids"])

        entry = {"exercise_name": display, "session_ids": session_ids}
        if client_ids:
            entry["client_ids"] = client_ids

        if key in lib_lookup:
            result["exact"].append(entry)
        else:
            # Try fuzzy: step name is substring of exactly one library name
            candidates = [n for n in lib_names if key in n]
            if len(candidates) == 1:
                result["fuzzy"].append({**entry, "matched_library_name": lib_lookup[candidates[0]].get('exercise_name', candidates[0])})
            else:
                # Try reverse: a library name is substring of the step name
                candidates = [n for n in lib_names if n in key]
                if len(candidates) == 1:
                    result["fuzzy"].append({**entry, "matched_library_name": lib_lookup[candidates[0]].get('exercise_name', candidates[0])})
                else:
                    result["unmatched"].append(entry)

    # ── 5. Summary ───────────────────────────────────────────
    result["summary"]["total_unique_names"] = len(name_registry)
    result["summary"]["exact_matches"]      = len(result["exact"])
    result["summary"]["fuzzy_matches"]      = len(result["fuzzy"])
    result["summary"]["no_matches"]         = len(result["unmatched"])

    logger.info(
        f"[Sheets] Exercise name audit: {result['summary']['total_unique_names']} unique names — "
        f"{result['summary']['exact_matches']} exact, "
        f"{result['summary']['fuzzy_matches']} fuzzy, "
        f"{result['summary']['no_matches']} unmatched"
    )


# ============================================================
# GARMIN WORKOUT SUPPORT
# ============================================================

def get_exercises_garmin_mapping(exercise_names: list) -> dict:
    """Look up garmin_exercise_name for a list of exercise names.

    Only returns entries where garmin_mapping_confidence is 'exact' or 'close'.
    Used by the /session/<id>/workout.fit endpoint to translate exercise names
    into FIT-compatible Garmin strings before calling exercise_mapper.lookup_exercise().

    Args:
        exercise_names: List of exercise_name strings from Plans_Steps.

    Returns:
        {exercise_name: garmin_exercise_name_string}
    """
    if not exercise_names:
        return {}

    try:
        ws = _get_worksheet(SHEET_NAMES['exercise_library'])
        rows = ws.get_all_records()

        name_set = {str(n).strip().lower() for n in exercise_names if n}
        mapping = {}
        for row in rows:
            name = str(row.get('exercise_name', '') or '').strip()
            if not name or name.lower() not in name_set:
                continue
            confidence  = str(row.get('garmin_mapping_confidence', '') or '').lower().strip()
            garmin_name = str(row.get('garmin_exercise_name', '') or '').strip()
            if confidence in ('exact', 'close') and garmin_name:
                mapping[name] = garmin_name

        return mapping

    except Exception as e:
        logger.warning(f"[Sheets] get_exercises_garmin_mapping failed: {e}")
        return {}

    return result
