"""
Exercise Library management tool.

Run from the backend/ directory:

    python scripts/exercise_lib.py read
        Prints all exercises as JSON to stdout (for analysis).

    python scripts/exercise_lib.py max-id
        Prints the highest ex_XXXX and wu_XXXX IDs currently in use.

    python scripts/exercise_lib.py summary
        Prints counts by category, body_region, movement_pattern,
        segment_type, and equipment — for gap analysis.

    python scripts/exercise_lib.py append <file.json>
        Reads a JSON array of exercise dicts from <file.json> and appends
        them to the Exercises_Library sheet. video_url is always left blank
        (to be added manually). Rows are written in the sheet's column order.
        Skips any row whose exercise_name already exists (case-insensitive).
"""

import json
import os
import re
import sys
from collections import Counter
from datetime import date

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
_TAB    = 'Exercises_Library'


def _connect():
    sa_json        = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']
    spreadsheet_id = os.environ['GOOGLE_SHEETS_SPREADSHEET_ID']
    creds  = Credentials.from_service_account_info(json.loads(sa_json), scopes=_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id)


def _worksheet():
    return _connect().worksheet(_TAB)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_read():
    ws   = _worksheet()
    rows = ws.get_all_records()
    print(json.dumps(rows, indent=2, ensure_ascii=False))


def cmd_max_id():
    ws   = _worksheet()
    rows = ws.get_all_records()

    ex_ids = []
    wu_ids = []
    for row in rows:
        eid = str(row.get('exercise_id', '')).strip()
        m = re.match(r'^ex_(\d+)$', eid)
        if m:
            ex_ids.append(int(m.group(1)))
        m = re.match(r'^wu_(\d+)$', eid)
        if m:
            wu_ids.append(int(m.group(1)))

    print(f"Highest ex_ ID : ex_{max(ex_ids):04d}" if ex_ids else "No ex_ IDs found")
    print(f"Highest wu_ ID : wu_{max(wu_ids):04d}" if wu_ids else "No wu_ IDs found")
    print(f"Total exercises: {len(rows)}")


def cmd_summary():
    ws   = _worksheet()
    rows = ws.get_all_records()

    def _count(field):
        c = Counter()
        for row in rows:
            val = str(row.get(field, '') or '').strip()
            for part in re.split(r'[;,]', val):
                part = part.strip()
                if part:
                    c[part] += 1
        return c

    for field in ('category', 'body_region', 'movement_pattern', 'segment_type', 'equipment', 'difficulty'):
        print(f"\n-- {field} --")
        for val, cnt in sorted(_count(field).items(), key=lambda x: -x[1]):
            print(f"  {cnt:>4}  {val}")

    print(f"\nTotal rows: {len(rows)}")


def cmd_append(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, encoding='utf-8') as f:
        new_exercises = json.load(f)

    if not isinstance(new_exercises, list):
        print("ERROR: JSON file must contain an array of exercise objects.", file=sys.stderr)
        sys.exit(1)

    ws      = _worksheet()
    headers = ws.row_values(1)          # exact column order from sheet row 1
    rows    = ws.get_all_records()

    # Build set of existing names for duplicate check
    existing_names = {str(r.get('exercise_name', '')).strip().lower() for r in rows}

    today = date.today().strftime('%d/%m/%Y')

    appended = 0
    skipped  = 0
    for ex in new_exercises:
        name = str(ex.get('exercise_name', '')).strip()
        if name.lower() in existing_names:
            print(f"  SKIP (already exists): {name}")
            skipped += 1
            continue

        # Build row in header order; video_url always blank
        row = []
        for col in headers:
            if col == 'video_url':
                row.append('')                      # left blank for manual review
            elif col == 'last_verified_date' and not ex.get(col):
                row.append(today)
            elif col == 'status' and not ex.get(col):
                row.append('active')
            else:
                row.append(str(ex.get(col, '') or ''))

        ws.append_row(row, value_input_option='USER_ENTERED')
        print(f"  ADDED: {name}")
        existing_names.add(name.lower())
        appended += 1

    print(f"\nDone — {appended} added, {skipped} skipped (already existed).")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'read':
        cmd_read()
    elif cmd == 'max-id':
        cmd_max_id()
    elif cmd == 'summary':
        cmd_summary()
    elif cmd == 'append':
        if len(sys.argv) < 3:
            print("Usage: python scripts/exercise_lib.py append <file.json>", file=sys.stderr)
            sys.exit(1)
        cmd_append(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)
