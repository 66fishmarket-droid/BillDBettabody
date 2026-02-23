# Exercise Group Generation System

## Overview

This system automatically parses the Exercise Library from Google Sheets and generates focused, token-efficient JSON files for each exercise group (Upper Push, Lower Pull, Swimming, etc.).

**Purpose:** Reduce token usage when Bill plans sessions by providing only relevant exercises instead of the entire 136+ exercise library.

**Token Savings:** ~95% reduction (from ~500K tokens to ~25K tokens per session planning)

---

## How It Works

### 1. Weekly Automation
- **Trigger:** GitHub Action runs every Sunday at midnight UTC
- **Process:** Fetches Exercise Library from Google Sheets → Parses into groups → Commits JSON files
- **Location:** Group files stored in `/exercise_groups/` directory

### 2. Exercise Groups Generated

| Group | Description | Typical Size |
|-------|-------------|--------------|
| `Upper_Push.json` | Horizontal & vertical pressing movements | ~13 exercises |
| `Upper_Pull.json` | Rows, pull-ups, lat work | ~15 exercises |
| `Lower_Push.json` | Squats, lunges (knee-dominant) | ~10 exercises |
| `Lower_Pull.json` | Deadlifts, hip thrusts (hip-dominant) | ~8 exercises |
| `Core.json` | Anti-movement, stability work | ~12 exercises |
| `Swimming.json` | All swimming strokes, drills, pool work | ~26 exercises |
| `Cardio.json` | Running, cycling, rowing | ~10 exercises |
| `Full_Body.json` | Compound movements, athletic exercises | ~10 exercises |

**Each group contains:**
- `main_exercises` - Primary exercises for this movement pattern
- `warmup_exercises` - Relevant warm-up exercises
- `cooldown_exercises` - Relevant cool-down/mobility work

### 3. Equipment Filtering

All exercises include an `equipment` field:
- `bodyweight` - Zero equipment needed
- `household` - Common household items (chairs, towels, etc.)
- `portable_accessory` - Bands, light dumbbells
- `free_weight` - Barbells, dumbbells, kettlebells
- `cable_system` - Cable machines
- `cardio_machine` - Treadmill, bike, rower
- `pool` - Swimming pool required

**Bill's Context Awareness:**
When planning sessions, Bill checks the client's equipment access and filters exercises accordingly. Someone with zero gym access only sees `bodyweight` and `household` exercises.

---

## File Structure

```
BillDBettabody/
├── .github/
│   └── workflows/
│       ├── test-sheets-connection.yml    # Connection test workflow
│       └── update-exercise-groups.yml    # Production workflow
├── scripts/
│   └── create_exercise_groups.py         # Main parsing script
├── exercise_groups/                       # Generated JSON files (auto-updated)
│   ├── Upper_Push.json
│   ├── Upper_Pull.json
│   ├── Lower_Push.json
│   ├── Lower_Pull.json
│   ├── Core.json
│   ├── Swimming.json
│   ├── Cardio.json
│   └── Full_Body.json
└── README.md                              # This file
```

---

## Setup Instructions

### Prerequisites
1. Google Cloud Project with Sheets API enabled
2. Service Account with JSON credentials
3. Exercise Library sheet shared with service account email
4. GitHub Secrets configured (see below)

### GitHub Secrets Required

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these three secrets:

1. **GOOGLE_SHEETS_CREDENTIALS**
   - Value: Entire contents of service account JSON file
   - Format: `{"type":"service_account","project_id":"...","private_key":"...",...}`

2. **EXERCISE_LIBRARY_SHEET_ID**
   - Value: Google Sheets spreadsheet ID (from URL)
   - Format: `1ABC_defGHI_123XYZ456`

3. **EXERCISE_LIBRARY_SHEET_NAME**
   - Value: Name of the worksheet/tab
   - Format: `Exercises_Library`

---

## Usage

### Manual Trigger (Recommended for Testing)

1. Go to **Actions** tab in GitHub
2. Select **"Update Exercise Groups"**
3. Click **"Run workflow"**
4. Select `develop` or `main` branch
5. Click **"Run workflow"**
6. Wait ~1 minute for completion
7. Check `/exercise_groups/` directory for updated files

### Automatic Weekly Updates

- Runs every Sunday at 00:00 UTC
- No manual intervention required
- Commits changes only if exercise library has been updated

### Backend Integration

When Bill plans a session:

```python
# Example: Fetch Upper Push exercises for a client with only bodyweight equipment

import requests

# Fetch group file from GitHub
url = "https://raw.githubusercontent.com/66fishmarket-droid/BillDBettabody/main/exercise_groups/Upper_Push.json"
response = requests.get(url)
group_data = response.json()

# Filter by client's available equipment
client_equipment = ['bodyweight', 'household']
available_exercises = [
    ex for ex in group_data['main_exercises']
    if ex['equipment'] in client_equipment
]

# Send to Claude API with context
prompt = f"""
You are planning an upper push session for a client with only bodyweight equipment.

Available exercises:
{json.dumps(available_exercises, indent=2)}

Select 3-5 exercises for today's session based on the client's training history.
"""
```

---

## JSON File Structure

Each group file follows this schema:

```json
{
  "group_name": "Upper_Push",
  "description": "Upper body pushing movements (horizontal and vertical presses)",
  "last_updated": "2026-02-01T12:00:00Z",
  "exercise_count": {
    "main": 13,
    "warmup": 5,
    "cooldown": 3,
    "total": 21
  },
  "main_exercises": [
    {
      "exercise_id": "ex_0123",
      "exercise_name": "Barbell Bench Press",
      "category": "strength",
      "body_region": "upper",
      "movement_pattern": "push_horizontal",
      "equipment": "free_weight",
      "primary_muscles": "pecs,triceps,anterior_delts",
      "segment_type": "main",
      "difficulty": "intermediate",
      "coaching_cues_short": "Retract scapulae, controlled descent, press to lockout",
      "safety_notes": "Use spotter for heavy sets; avoid bouncing bar",
      "regression": "Dumbbell Bench Press",
      "progression": "Pause Bench Press"
    }
  ],
  "warmup_exercises": [...],
  "cooldown_exercises": [...]
}
```

---

## Fields Included in Each Exercise

**Essential (always present):**
- `exercise_id` - Unique identifier (required for database operations)
- `exercise_name` - Human-readable name
- `category` - strength, conditioning, core, mobility, swimming, power
- `body_region` - upper, lower, core, full
- `movement_pattern` - push_horizontal, pull_vertical, squat, hinge, etc.
- `equipment` - Determines accessibility for different clients
- `segment_type` - main, warmup, accessory

**Included if available:**
- `primary_muscles` - Load distribution awareness
- `difficulty` - beginner, intermediate, advanced
- `coaching_cues_short` - Quality control reference
- `safety_notes` - Critical for Bill's safety-first approach
- `regression` - Easier variation for scaling down
- `progression` - Harder variation for scaling up
- `training_focus` - strength,hypertrophy, endurance,aerobic, etc.
- `secondary_muscles` - Supporting muscle groups
- `special_flags` - joint_friendly, low_impact, shoulder_intensive, etc.

**Excluded (too verbose for token efficiency):**
- `exercise_description_long` - Detailed explanations (can fetch separately if needed)
- `common_mistakes` - Not needed for exercise selection
- `video_url` - Can be fetched when exercise is selected
- `garmin_*` fields - Not relevant for session planning

---

## Maintenance

### Adding New Exercises

1. Add exercise to Google Sheets (Exercises_Library tab)
2. Wait for next weekly run (Sunday midnight UTC)
3. **OR** manually trigger the workflow (Actions → Update Exercise Groups → Run workflow)
4. New exercise automatically appears in relevant group files

### Modifying Grouping Logic

Edit `scripts/create_exercise_groups.py`:
- Modify filtering criteria in `generate_all_groups()` method
- Add new groups by copying existing group patterns
- Test locally before committing

### Testing Changes Locally

```bash
# Set environment variables
export GOOGLE_CREDENTIALS='{"type":"service_account",...}'
export SHEET_ID='1ABC_defGHI_123XYZ456'
export SHEET_NAME='Exercises_Library'

# Run script
python scripts/create_exercise_groups.py

# Check generated files
ls -lh exercise_groups/
```

---

## Troubleshooting

### Workflow Fails: "Spreadsheet not found"
- Check that Spreadsheet ID is correct in GitHub Secrets
- Verify sheet is shared with service account email (from JSON credentials)

### Workflow Fails: "Worksheet not found"
- Check sheet name is exactly `Exercises_Library` (case-sensitive)
- Verify in GitHub Secrets: `EXERCISE_LIBRARY_SHEET_NAME`

### No Changes Committed
- This is normal if no exercises were added/modified since last run
- Check workflow logs to confirm it ran successfully

### Exercise Missing from Group File
- Check exercise has correct `body_region` and `movement_pattern` fields
- Review filtering logic in `create_exercise_groups.py`
- Exercise may be filtered out by segment_type (warmup exercises excluded from main lists)

### Token Usage Still High
- Verify backend is fetching group files, not full library
- Check which fields are being sent to Claude API
- Consider excluding more verbose fields if needed

---

## Roadmap

### Phase 1 (Current)
- ✅ Weekly automated group generation
- ✅ Equipment-based filtering support
- ✅ Warm-up/cool-down separation

### Phase 2 (Future)
- [ ] Backend integration with Bill's session planning
- [ ] Equipment availability checking against client profile
- [ ] Progressive overload tracking (difficulty progression over time)

### Phase 3 (Future)
- [ ] Exercise popularity analytics (which exercises are most used)
- [ ] Automatic regression/progression chain validation
- [ ] Multi-language support for exercise names

---

## Support

Questions or issues? Check:
1. GitHub Actions logs (Actions tab → Recent workflow runs)
2. Exercise Library sheet (verify data structure)
3. Test connection workflow (ensure API access is working)

---

## License & Credits

Part of the Bill D'Bettabody migration project.  
Exercise Library maintained in Google Sheets.  
Automation powered by GitHub Actions.
