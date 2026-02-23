# E2E Test Handover — 2026-02-21

## Start Servers

```bash
# Terminal 1 — Backend
cd backend && python server.py

# Terminal 2 — Frontend
cd frontend/bill-pwa && python -m http.server 8080

# Health check
curl http://localhost:5000/health
```

---

## Screen 1: Login (`http://localhost:8080`)

**Actions:**
- Enter client ID (e.g. `plaasboy`) and click Enter

**Expect:**
- "Connecting..." appears on button while `/initialize` fires
- Greeting from Bill loads and displays
- `bill_session` saved to localStorage (`{session_id, client_id}`)
- `bill_greeting` saved to localStorage
- Redirected to `dashboard.html`

**Console to watch:**
- `[App] Loaded session: plaasboy`
- No 404s (icon 404 should now be gone)

**If it breaks:**
- Open DevTools → Network → check `/initialize` POST response
- Should return `{session_id, client_id, greeting, state}`

---

## Screen 2: Dashboard (`dashboard.html`)

**Actions:**
- Page loads automatically after login

**Expect:**
- Client name appears in "Your Progress" card
- Sessions Done count shows (may be 0)
- Week number shows (e.g. "Week 1")
- Today's Session card shows: focus, phase, location, duration
- **Calories and Protein show real numbers** (not `—`) — from Plans_Blocks
- **Supplement list appears** below nutrition stats — from Plans_Blocks
- "Start Session" button visible

**Console to watch:**
- `[Sheets] Block blk_...: nutrition_targets=True, supplements=3`
- `[Dashboard] Dashboard loaded:` object in console — verify `nutrition_targets` has values

**If nutrition shows `—`:**
- Check Plans_Blocks sheet: `block_id` on the next session row must match a block in Plans_Blocks
- Check Plans_Sessions → `block_id` column is populated
- Check Plans_Blocks → `nutrition_targets` column is valid JSON e.g. `{"calories":2500,"protein":160,"carbs":250,"fat":80}`

**If supplement list is missing:**
- Check Plans_Blocks → `supplement_protocol` — must be comma-separated JSON objects:
  `{"name":"Creatine","dosage":"5g","timing":"daily"}, {"name":"..."}`

---

## Screen 3: Chat (`chat.html`)

**Actions:**
- Click "💬 Talk to Bill"
- Type a message and send

**Expect:**
- Bill's greeting pre-loaded from `bill_greeting` localStorage (the one from login)
- Message sends, typing indicator appears
- Bill responds (may take 10–30s for first response)
- "← Back" returns to dashboard

**Console to watch:**
- `[Chat] Sending message...`
- No 401/400 errors on `/chat`

---

## Screen 4: Session Preview (`session-preview.html`)

**Actions:**
- From dashboard click "Start Session"

**Expect:**
- Session title = session focus (e.g. "Lower Body Strength")
- Session summary text below title
- Phase name, location, duration (~45 min or actual value), intensity
- Warm-up / Main / Cool-down exercise lists populated
- Equipment list shows real equipment from Exercise Library (not name-matched guesses)
- "Ask Bill" navigates to chat
- "← Back" returns to dashboard

**Console to watch:**
- `[Session Preview] Steps loaded: X`

**If phase/duration wrong:**
- These fields were recently fixed — if still blank, check `app.getActiveSession()` in console
- Should have `phase_name` and `estimated_duration` (not `phase` or `estimated_duration_minutes`)

---

## Screen 5: Session Active (`session-active.html`)

**Actions:**
- Click "START SESSION" on preview

**Expect:**
- Session title and subtitle render (focus + date)
- Exercise cards appear in order (Warm-Up → Main → Cool-Down) with colour-coded segment badges
- Each main exercise shows:
  - `exercise_description_short` below the exercise name (small muted text)
  - Prescription block (sets × reps @ load, tempo, RPE targets, coach notes)
  - Set rows (prescribed number by default, up to 10 with "+ Add Set")
  - Unit selector
  - Per-set RPE inputs
  - ▶ Watch button (if `video_url` present) and 📖 Details button (if description present)
- "📖 Terms" glossary panel toggles
- "💬 Ask Bill" links to chat

**Log some sets:**
- Enter reps, value (weight/time), RPE for a few sets on at least one main exercise
- Try "+ Add Set" button
- Open 📖 Details modal on an exercise — check description, safety notes, regression/progression

**Complete the session:**
- Scroll to bottom
- Enter Overall RPE (1–10)
- Click "Complete Session"
- Loading spinner shows ("Submitting session...")
- Redirected to Session Complete screen

**Console to watch:**
- `[Sheets] Exercise_Library joined: X/Y steps matched` (in backend terminal)
- `[Session Active] Submit payload:` — check steps_upsert array is populated
- `/session/<id>/complete` POST returns 200

**If exercise library fields missing (no Watch/Details buttons):**
- Check backend terminal for `Exercise_Library joined: 0/X` — exercise_name in Plans_Steps
  must match exercise_name in Exercise_Library exactly (case-insensitive)

---

## Screen 6: Session Complete (`session-complete.html`)

**Expect:**
- Green ✓ circle
- "Session Complete" heading
- Subheading: `[focus] · [date]`
- Stats: exercise count (main only), session RPE (if entered), location
- List of main exercises with ✓ prefix
- Motivational quote from Bill (random)
- "Back to Dashboard" button → clears `bill_session_summary` → back to dashboard

---

## Screen 7: Progress Screen (`progress.html`)

**Actions:**
- From dashboard click "View Progress & History →"

**Expect:**
- Group cards appear (Upper Push, Upper Pull, Lower Body, etc.)
- Each shows avg % improvement and exercise count
- Click a group → accordion expands
- Each exercise shows:
  - Name + % improvement badge (green = positive)
  - Three horizontal bars: Started (muted) / Recent (chocolate) / Best (green)
  - Values and units labelled
  - Session count below bars
- "Recent" bar only appears if actual session data was ever submitted

**If groups are empty:**
- Requires Exercise_Bests sheet to have data for this client
- Groups depend on Exercise_Library join — if exercise_name doesn't match, it lands in "Other"

**Console to watch:**
- `[Sheets] Progress for plaasboy: X groups, Y exercises` (backend terminal)

---

## Things That Need Real Data to Verify

| Feature | What to check |
|---|---|
| Nutrition targets | Real numbers in calories/protein fields |
| Supplement list | Items appear below nutrition stats |
| Exercise Library join | Watch/Details buttons appear on exercise cards |
| Session write to Sheets | After complete, check Plans_Steps rows have `completed_timestamp` |
| Exercise Bests V2 | After complete, check Exercise_Bests sheet updated (may take a minute) |
| Progress % | Only shows data if Exercise_Bests has `first_value` + `current_value` |

---

## Quick Debug Snippets (Browser Console)

```javascript
// Check what session is stored
JSON.parse(localStorage.getItem('bill_session'))

// Check active session handed to session-preview
JSON.parse(localStorage.getItem('bill_active_session'))

// Check steps handed to session-active
JSON.parse(localStorage.getItem('active_session_steps'))

// Check session summary on complete screen
JSON.parse(localStorage.getItem('bill_session_summary'))

// Clear everything and start fresh
['bill_session','bill_active_session','active_session_steps',
 'bill_session_summary','bill_greeting'].forEach(k => localStorage.removeItem(k))
```

---

## Known Limitations (Not Bugs)

- Training plan chat response can take ~2 min (hits max_tokens 4096) — valid UX, not a crash
- Progress screen "Recent" bar missing = no actuals have been submitted yet for that exercise
- Equipment card hidden on session-preview if Exercise Library has no `equipment` data for those exercises
- `sessions-completed` stat on dashboard always shows 0 (profile endpoint doesn't return this yet)

---

## What's Left After E2E

- Merge `develop` → `main` once E2E passes
- Deploy to Railway (backend) + hosting (frontend)
- Real PWA icons (PNG 192/512) for iOS home screen support
