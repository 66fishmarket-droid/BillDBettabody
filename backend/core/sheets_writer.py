"""
Bill D'Bettabody - Google Sheets Writer

Writes user session completion data directly to Plans_Steps.
Intended for athlete-entered session logging (not Bill edits).
"""

import os
import json
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SHEET_NAMES = {
    'plans_steps':    'Plans_Steps',
    'plans_sessions': 'Plans_Sessions',
}

_spreadsheet = None


def _get_spreadsheet():
    global _spreadsheet

    if _spreadsheet is not None:
        return _spreadsheet

    sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID')

    if not sa_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set.")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_SPREADSHEET_ID not set.")

    try:
        sa_info = json.loads(sa_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON invalid JSON: {e}")

    try:
        creds = Credentials.from_service_account_info(sa_info, scopes=_SCOPES)
        client = gspread.authorize(creds)
        _spreadsheet = client.open_by_key(spreadsheet_id)
        logger.info("[Sheets Writer] Connected to Google Spreadsheet")
        return _spreadsheet
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Google Sheets: {e}")


def _get_worksheet(sheet_name):
    spreadsheet = _get_spreadsheet()
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        raise RuntimeError(f"Sheet tab '{sheet_name}' not found.")


def update_steps_actuals(step_updates, status='completed', completed_timestamp=None):
    """
    Update Plans_Steps rows by step_id with athlete-entered actuals.

    Args:
        step_updates (list[dict]): Each dict must include step_id and any actual_* fields.
        status (str): Value to write into status column (if provided).
        completed_timestamp (str): ISO timestamp; if None, uses utcnow().

    Returns:
        dict: { updated: int, missing: int }
    """
    if not step_updates:
        return {'updated': 0, 'missing': 0}

    ws = _get_worksheet(SHEET_NAMES['plans_steps'])

    headers = ws.row_values(1)
    if not headers:
        raise RuntimeError("Plans_Steps header row is empty.")

    header_index = {h: i + 1 for i, h in enumerate(headers)}
    step_id_col = header_index.get('step_id')
    if not step_id_col:
        raise RuntimeError("Plans_Steps missing 'step_id' header.")

    # Build step_id -> row index map
    step_ids = ws.col_values(step_id_col)
    step_row_map = {}
    for idx, val in enumerate(step_ids, start=1):
        if idx == 1:
            continue
        if val:
            step_row_map[str(val)] = idx

    allowed_fields = [
        'notes_athlete', 'status', 'completed_timestamp',
        'metric_key', 'metric_context_key',
        'actual_set1_reps',  'actual_set2_reps',  'actual_set3_reps',
        'actual_set4_reps',  'actual_set5_reps',  'actual_set6_reps',
        'actual_set7_reps',  'actual_set8_reps',  'actual_set9_reps',
        'actual_set10_reps',
        'actual_set1_value',  'actual_set2_value',  'actual_set3_value',
        'actual_set4_value',  'actual_set5_value',  'actual_set6_value',
        'actual_set7_value',  'actual_set8_value',  'actual_set9_value',
        'actual_set10_value',
        'actual_set1_metric',  'actual_set2_metric',  'actual_set3_metric',
        'actual_set4_metric',  'actual_set5_metric',  'actual_set6_metric',
        'actual_set7_metric',  'actual_set8_metric',  'actual_set9_metric',
        'actual_set10_metric',
        'actual_set1_rpe',  'actual_set2_rpe',  'actual_set3_rpe',
        'actual_set4_rpe',  'actual_set5_rpe',  'actual_set6_rpe',
        'actual_set7_rpe',  'actual_set8_rpe',  'actual_set9_rpe',
        'actual_set10_rpe',
    ]

    timestamp = completed_timestamp or datetime.utcnow().isoformat()

    updates = []
    missing = 0

    for step in step_updates:
        step_id = str(step.get('step_id', '')).strip()
        if not step_id:
            continue

        row = step_row_map.get(step_id)
        if not row:
            missing += 1
            continue

        # Always set status and completed_timestamp
        step['status'] = status
        step['completed_timestamp'] = timestamp

        for field in allowed_fields:
            if field not in step:
                continue
            col = header_index.get(field)
            if not col:
                continue
            value = step.get(field)
            if value is None:
                continue
            updates.append({
                'range': gspread.utils.rowcol_to_a1(row, col),
                'values': [[value]]
            })

    if updates:
        ws.batch_update(updates)

    return {'updated': len(updates), 'missing': missing}


def update_session_status(session_id, status='completed', session_notes=None, session_summary=None):
    """
    Update Plans_Sessions row for a given session_id.

    Sets session_status on every call.
    Optionally updates session_notes and session_summary if provided.

    Plans_Sessions headers (relevant):
      session_id, session_status, session_notes, session_summary

    Args:
        session_id (str): The session identifier.
        status (str): Value for session_status column (default 'completed').
        session_notes (str | None): Athlete notes; skipped if None.
        session_summary (str | None): Session summary text; skipped if None.

    Returns:
        dict: { 'updated': True } if the row was found and updated,
              { 'updated': False, 'reason': '...' } otherwise.
    """
    if not session_id:
        return {'updated': False, 'reason': 'No session_id provided'}

    ws = _get_worksheet(SHEET_NAMES['plans_sessions'])

    headers = ws.row_values(1)
    if not headers:
        raise RuntimeError("Plans_Sessions header row is empty.")

    header_index = {h: i + 1 for i, h in enumerate(headers)}

    session_id_col = header_index.get('session_id')
    if not session_id_col:
        raise RuntimeError("Plans_Sessions missing 'session_id' header.")

    status_col   = header_index.get('session_status')
    notes_col    = header_index.get('session_notes')
    summary_col  = header_index.get('session_summary')

    # Find the row matching session_id
    all_session_ids = ws.col_values(session_id_col)
    target_row = None
    for idx, val in enumerate(all_session_ids, start=1):
        if idx == 1:
            continue  # skip header
        if str(val).strip() == str(session_id).strip():
            target_row = idx
            break

    if not target_row:
        logger.warning(f"[Sheets Writer] session_id '{session_id}' not found in Plans_Sessions")
        return {'updated': False, 'reason': f"session_id '{session_id}' not found"}

    updates = []

    if status_col:
        updates.append({
            'range': gspread.utils.rowcol_to_a1(target_row, status_col),
            'values': [[status]]
        })

    if session_notes is not None and notes_col:
        updates.append({
            'range': gspread.utils.rowcol_to_a1(target_row, notes_col),
            'values': [[session_notes]]
        })

    if session_summary is not None and summary_col:
        updates.append({
            'range': gspread.utils.rowcol_to_a1(target_row, summary_col),
            'values': [[session_summary]]
        })

    if updates:
        ws.batch_update(updates)
        logger.info(
            f"[Sheets Writer] Updated Plans_Sessions row {target_row} "
            f"for session_id '{session_id}': status={status}, "
            f"notes={'set' if session_notes is not None else 'skipped'}, "
            f"summary={'set' if session_summary is not None else 'skipped'}"
        )

    return {'updated': True}
