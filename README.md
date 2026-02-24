# Bill D'Bettabody

An AI personal trainer and coaching assistant powered by Claude AI, Make.com automation, Google Sheets, and a React-free Progressive Web App.

Bill is a gruff-but-warm coach who builds personalised training blocks, populates weekly sessions, tracks exercise bests, handles injuries, and runs autonomously on a Sunday night to make sure every client is set up for the week ahead.

---

## What's Live

### Backend (Railway)
Flask API handling all client interactions, session management, and direct Sheets I/O:

| Endpoint | Purpose |
|---|---|
| `POST /initialize` | Identify client (stranger / onboarding / ready) and load context |
| `POST /chat` | Main chat — Bill responds with tool use (Make.com webhook calls) |
| `GET /dashboard` | PWA home screen data (next session, exercise bests, block summary) |
| `GET /week` | All sessions for the client's current training week |
| `GET /session/<id>` | Full session detail with planned steps |
| `POST /session/<id>/complete` | Write actual sets/reps/loads and mark session done |
| `GET /progress` | Progress screen — exercise bests history, lifetime stats |
| `GET /profile` | Client profile from active session context |
| `GET /sessions/rest-day-summary` | Bill generates a contextual rest day message |
| `POST /admin/weekly-prep` | Trigger Sunday auto-prep manually (scoped to one client or all) |
| `GET /diag/exercise-names` | Audit Plans_Steps exercise names against the library |

### Frontend (PWA)
Multi-page Progressive Web App — no framework, vanilla JS:

| Screen | File |
|---|---|
| Login / identity | `index.html` |
| Dashboard | `dashboard.html` |
| Week view | `week.html` |
| Session preview | `session-preview.html` |
| Active session | `session-active.html` |
| Session complete | `session-complete.html` |
| Chat with Bill | `chat.html` |
| Progress | `progress.html` |

### Make.com Scenarios (13 blueprints)
All blueprints are stored in `backend/scripts/make_blueprints/`:

| Scenario | Purpose |
|---|---|
| Load Client Context V2 | Assembles full client context from Sheets for Bill |
| Full Training Block Generator | Creates a multi-week periodised training block |
| Populate Training Week | Fills next week's sessions and steps |
| Session Update | Updates a specific session or step |
| Exercise Filter | Filters exercises by body region, equipment, movement pattern |
| Exercise Bests | Tracks and updates personal bests after session completion |
| Daily Email Generator | Sends the daily session summary email |
| Plan Reminder | Sunday morning check — emails client if next week isn't set up |
| Add Injury | Logs a new injury and contraindication |
| Update Injury Status | Marks an injury as resolved or updated |
| Add Chronic Condition | Logs a permanent health condition |
| Issue Log Updater | Records client-reported issues |
| User Upsert | Creates or updates a client record |

### Sunday Automation
Two-layer system ensuring every client is set up for Monday:

1. **Sunday morning** — Make.com checks `Plans_Weeks` and `Plans_Steps`. If the upcoming week has no steps, sends the client a reminder email with a link to open the app.
2. **Sunday 23:00 UTC** — APScheduler job runs inside Railway. Finds any clients still without steps and asks Bill to auto-populate their week, so everything is ready first thing Monday.

---

## Architecture

```
Client (PWA)
    │
    ▼
Flask API (Railway)
    ├── Claude API (Anthropic) ──► Bill's coaching logic + tool use
    ├── Google Sheets (direct) ──► Plans_Sessions, Plans_Steps,
    │                              Exercise_Bests, Exercises_Library
    └── Make.com (webhooks) ─────► Training block/week generation,
                                   exercise filters, injury logging,
                                   client context assembly, email
```

**Data flow:**
- Reads: Python → Google Sheets directly (`sheets_client.py`)
- Writes (session actuals): Python → Google Sheets directly (`sheets_writer.py`)
- Writes (everything else): Bill → tool call → Make.com webhook → Google Sheets

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI | Claude API (Anthropic) — `claude-sonnet-4-6` |
| Backend | Python 3, Flask 3.0, APScheduler |
| Automation | Make.com (13 scenarios) |
| Data store | Google Sheets (via gspread) |
| Frontend | Vanilla JS PWA (no framework) |
| Hosting | Railway (backend), GitHub Pages or static host (frontend) |

---

## Project Structure

```
BillDBettabody/
├── backend/
│   ├── server.py              # All Flask routes
│   ├── config.py              # Environment config
│   ├── requirements.txt
│   ├── core/
│   │   ├── claude_client.py   # Claude API + tool calling
│   │   ├── sheets_client.py   # Google Sheets reader
│   │   ├── sheets_writer.py   # Google Sheets writer (actuals)
│   │   ├── bill_config.py     # Operating modes, client states
│   │   ├── context_loader.py  # Session greeting logic
│   │   └── tool_definitions.py
│   ├── webhooks/
│   │   ├── webhook_handler.py # Make.com webhook calls
│   │   └── context_integrity.py
│   ├── models/
│   │   └── client_context.py  # In-memory session store
│   └── scripts/
│       └── make_blueprints/   # All Make.com scenario blueprints
├── frontend/
│   └── bill-pwa/
│       ├── index.html
│       ├── dashboard.html
│       ├── chat.html
│       ├── session-active.html
│       ├── session-complete.html
│       ├── session-preview.html
│       ├── week.html
│       ├── progress.html
│       ├── css/app.css
│       ├── js/                # Per-screen JS modules
│       ├── manifest.json
│       └── sw.js              # Service worker
├── Backlog/
│   ├── Completed/             # Shipped features
│   └── *.txt                  # Upcoming features
└── docs/
    ├── BILL_REQUIREMENTS_CANONICAL.md
    ├── PWA_FRONTEND_SCOPE.md
    └── GPT Instructions/      # Bill's system instructions + reference tables
```

---

## Local Development

```bash
# Clone
git clone https://github.com/66fishmarket-droid/BillDBettabody.git
cd BillDBettabody/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, Google service account credentials,
# Make.com webhook URLs

# Run
python server.py
```

The backend starts on `http://localhost:5000`.

---

## Key Documentation

- **[Requirements (canonical)](docs/BILL_REQUIREMENTS_CANONICAL.md)** — complete system spec (Parts 1–7)
- **[Frontend scope](docs/PWA_FRONTEND_SCOPE.md)** — PWA screen designs and data contracts
- **[Bill's Instructions](docs/GPT%20Instructions/Bill_Instructions_V2.txt)** — coaching rules, nutrition logic, safety behaviour
- **[Calculations Reference](docs/GPT%20Instructions/Bill_Calculations_Reference.txt)** — 1RM formulas, HR zone tables, estimation tables
- **[Scenario Helper Instructions](docs/GPT%20Instructions/Scenario_helper_instructions_V2.txt)** — Make.com data handling rules
- **[Backlog](Backlog/README.md)** — upcoming features and roadmap

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `GOOGLE_SHEETS_CREDENTIALS` | Service account JSON (base64 or path) |
| `GOOGLE_SHEETS_ID` | Target spreadsheet ID |
| `MAKE_WEBHOOK_*` | URLs for each Make.com scenario |
| `FLASK_ENV` | `production` or `development` |
| `PORT` | Server port (Railway sets this automatically) |
