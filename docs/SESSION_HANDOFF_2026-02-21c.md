# Session Handoff — 2026-02-21c

## What We Did This Session

### 1. Generated New Training Block
- User asked Bill to create a new block re-introducing running (2 run days + 2 gym/swim days + 1 gym-only day)
- Bill correctly created the block but violated the discussion-first rule (fired week population without asking)
- This exposed several bugs that were fixed below

---

### 2. Rate Limit Retry — FIXED ✓
**Problem:** `chat_with_tools` had no retry logic for 429 errors. With a ~33k token system prompt, Round 1 exhausts the 30k/min token bucket. Round 2 (returning tool results) fires immediately and crashes.

**Fix:** Added exponential backoff retry loop in `claude_client.py`. On 429, waits 60s/120s/180s per retry (max 3 retries) before re-sending the round.

**File:** `backend/core/claude_client.py`

---

### 3. `update_contraindication_temp` Schema Mismatch — FIXED ✓
**Problem:** Make.com scenario 11 matches rows by `client_id` + `description` (exact injury text). Our OpenAPI schema and validator required `record_id` instead. Bill sent `record_id` without `description` → Make.com `filterRows` crashed → 500.

**Fix:**
- OpenAPI schema: replaced `record_id` (required) with `description` (required)
- Webhook validator schema: same change
- Description must exactly match the text from the client context injuries string (segment between 2nd and 3rd pipe)

**Files:** `backend/core/schemas/bill_actions_openapi.json`, `backend/webhooks/webhook_schemas.py`

---

### 4. Bill Behaviour — Discussion First Rule — FIXED ✓
**Problem:** Bill fired `update_contraindication_temp` in the same turn as receiving the user's initial message (no discussion, no confirmation). The PRE-WRITE rule existed but didn't stop first-turn tool calls.

**Fix:** Added `DISCUSS FIRST RULE` to `Bill_Instructions_V2.txt` section 2.1g:
- Bill must respond conversationally (acknowledge, ask questions) before calling any write tool
- NEVER make a write tool call in the same turn as the initial user message
- Injury mentions specifically require explicit confirmation in a subsequent message before `update_contraindication_temp` fires

**File:** `docs/GPT Instructions/Bill_Instructions_V2.txt`

---

### 5. `nutrition_targets` Type Mismatch — FIXED ✓
**Problem:** OpenAPI schema said `nutrition_targets` was `type: object`. Bill sent a JSON object. Webhook validator expected `type: string`. Validation failed → payload retried without `nutrition_targets` → empty cell in Plans_Blocks → dashboard showed `—`.

Same issue for `supplement_protocol` (`type: array` vs `type: string`).

**Fix:**
- OpenAPI schema: both fields changed to `type: string` with explicit example and description mandating serialization as JSON string before sending
- Webhook validator: `nutrition_targets` added to `plan.required` with `minLength: 10` — omitting it is now a hard error
- Scenario 09 instructions: added `SERIALIZATION RULE` section with correct/incorrect examples

**Files:** `backend/core/schemas/bill_actions_openapi.json`, `backend/webhooks/webhook_schemas.py`, `docs/scenarios/09_full_training_block_generator.txt`

---

### 6. Sessions Done Count — FIXED ✓
**Problem:** Dashboard "Sessions Done" stat always showed 0. `/profile` endpoint returns `client_profile` from context which has no `completed_sessions` field.

**Fix:** `get_dashboard_data()` now counts completed sessions from `all_sessions` (already loaded — no extra sheet read). Added `completed_sessions` to the result dict. `dashboard.js` reads from `this.dashboard.completed_sessions` first.

**Files:** `backend/core/sheets_client.py`, `frontend/bill-pwa/js/dashboard.js`

---

### 7. This Week View — NEW ✓
**Problem:** No way to see the upcoming training week at a glance.

**Fix:**
- New `get_week_sessions(client_id)` in `sheets_client.py` — returns all sessions in the same `week_id` as the next upcoming session, with main exercise names per session
- New `/week` GET endpoint in `server.py`
- New `week.html` + `week.js` — day tiles showing date chip, focus, location, duration, RPE, exercise list. Completed sessions appear faded.
- Added `getWeek()` to `api.js`
- "📅 This Week →" link added to dashboard alongside "View Progress & History →"

**Files:** `backend/core/sheets_client.py`, `backend/server.py`, `frontend/bill-pwa/week.html`, `frontend/bill-pwa/js/week.js`, `frontend/bill-pwa/js/api.js`, `frontend/bill-pwa/dashboard.html`

---

### 8. Progress Screen Error — PARTIALLY FIXED ✓
**Problem:** "View Progress & History" button shows an error rather than redirecting cleanly when session is expired (common after server restart).

**Fix:** `progress.js` now guards against missing `app.sessionId` before the API call, and redirects to login on a 400 response rather than showing a dead alert.

The underlying progress data error (if it persists after a clean login) needs further investigation — share backend terminal output when it errors.

**File:** `frontend/bill-pwa/js/progress.js`

---

## Manual Sheet Updates Required

The Plans_Blocks row created this session has empty `nutrition_targets` and `supplement_protocol` cells (written before the type fix). Paste these directly into the sheet:

**nutrition_targets** (col K):
```
{"calories": 2900, "protein": 165, "carbs": 500, "fat": 20}
```

**supplement_protocol** (col L):
```
[{"name": "Creatine", "dosage": "3-5g", "timing": "daily, any time"}, {"name": "Omega-3", "dosage": "2-3g", "timing": "daily"}, {"name": "Vitamin D", "dosage": "", "timing": "daily (winter months)"}, {"name": "Magnesium", "dosage": "", "timing": "optional, daily"}, {"name": "Multivitamin", "dosage": "", "timing": "optional, daily"}]
```

---

## Current State

**Branch:** `develop` (5 commits ahead of origin)
**Backend:** ~97% complete
**Frontend:** ~70% complete

### What's Working
- Login → Dashboard → Chat → Training plan generation → Week population
- Sessions Done count (live from sheet)
- This Week view (new)
- Session flow: Preview → Active → Complete → Dashboard
- Rate limit retries (won't crash on multi-round tool calls)
- Contraindication update schema now correct

### Known Remaining Issues

| Issue | Status |
|---|---|
| Progress screen error (if not session expiry) | Needs backend log to diagnose |
| Nutrition targets on dashboard | Will work for new blocks — existing block needs manual sheet fix above |
| `update_contraindication_temp` still fires without discussion | Instruction fix added — needs testing |
| Bill populating week immediately after block creation | Instruction fix added — needs testing |
| Vitamin D / Magnesium dosages blank in supplement protocol | Fill in manually if desired |

### Next Session Priorities
1. Restart backend + re-login → test progress screen with clean session
2. Start a session to verify the week view and session flow end-to-end
3. Complete a session and verify Plans_Steps writes + Exercise_Bests update
4. Confirm Bill now asks before all writes (test with a training block request)
5. Push `develop` → `main` once E2E passes cleanly

---

## Server Commands

```bash
# Backend
cd backend && python server.py

# Frontend
cd frontend/bill-pwa && python -m http.server 8080

# Health check
curl http://localhost:5000/health
```
