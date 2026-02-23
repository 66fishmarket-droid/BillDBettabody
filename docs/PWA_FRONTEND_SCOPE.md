# Bill D'Bettabody - PWA Frontend Scope Document

**Version:** 1.0
**Date:** February 17, 2026
**Status:** DESIGN APPROVED - Ready for implementation
**Purpose:** Define the UI design, architecture, and build scope for the Bill PWA frontend

---

## Design Decisions Summary

| Decision | Choice |
|----------|--------|
| App structure | Single-Page App (one HTML shell, JS view swapping) |
| Visual theme | Dark & Warm (charcoal + brown/wheat — current palette) |
| CSS approach | Custom CSS only (remove Tailwind CDN, build on app.css) |
| Home screen | Info cards top + Bill chat below, input pinned at bottom |
| Chat prominence | Integrated into home screen, not a separate page |
| Session logging | Separate full-screen view, user-controlled exercise order |
| Navigation | Hub-and-spoke (home is hub, no persistent nav bar) |
| Bill's avatar | Large on login screen, small circle on chat messages + headers elsewhere |
| Target devices | Mobile-first, desktop aware |

---

## Architecture

### Single-Page App Structure

```
index.html (shell)
├── css/app.css (all styling, no Tailwind)
├── js/app.js (router, session management, shared utilities)
├── js/api.js (backend communication)
├── js/views/login.js (login / welcome screen, device recognition)
├── js/views/home.js (home screen: info cards + chat)
├── js/views/session-preview.js (pre-workout overview)
├── js/views/session-active.js (in-session logging)
├── js/views/session-complete.js (post-session summary)
├── js/views/progress.js (history & stats — future)
├── js/components/chat.js (chat message handling, Bill's avatar)
├── js/components/exercise-card.js (expandable exercise detail)
├── js/components/step-input.js (set/rep/weight/time data entry)
├── js/mock-data.js (development helper)
├── sw.js (service worker)
├── manifest.json (PWA config)
└── assets/
    ├── bill-portrait.png (optimise to <50KB)
    └── icons/ (192x192, 512x512 PWA icons)
```

### SPA Router

- Hash-based routing (`#/login`, `#/home`, `#/session-preview`, `#/session-active`, etc.)
- Single `<div id="app">` mount point in `index.html`
- Each view module exports `render()` and `destroy()` methods
- Back navigation via browser history API
- View transitions: simple fade or slide (CSS-driven, no library)

### View Lifecycle

```
Router detects hash change
  → Call current view's destroy() (cleanup listeners)
  → Call new view's render() (inject HTML, bind events)
  → Update browser history
```

---

## Views

### 0. Login / Welcome (`#/login`)

First screen the user sees. Handles both first-time registration and returning user recognition.

#### First-Time User

```
┌─────────────────────────────┐
│                             │
│      ┌──────────────┐       │
│      │              │       │
│      │  Bill's      │       │
│      │  Portrait    │       │
│      │  (LARGE)     │       │
│      │              │       │
│      └──────────────┘       │
│                             │
│   Bill D'Bettabody          │
│   Your AI Fitness Coach     │
│                             │
│ ┌─────────────────────────┐ │
│ │ Enter your Client ID:   │ │
│ │ [____________________]  │ │
│ │                         │ │
│ │ New here? Bill will     │ │
│ │ get you set up.         │ │
│ │                         │ │
│ │ [  Let's Go  ]          │ │
│ └─────────────────────────┘ │
│                             │
└─────────────────────────────┘
```

- **Bill's portrait displayed LARGE** — this is the branding/personality moment
- Client ID input field (for existing users rejoining on a new device)
- "New here?" path for first-time users (Bill handles onboarding via chat)
- On submit: `POST /initialize` with `client_id` → backend returns session + context

#### Returning User (Auto-Recognition)

- On app load, check localStorage for stored `client_id` + device fingerprint
- If recognised: **skip login entirely**, go straight to `#/home`
- The stored `client_id` is passed to the backend on the very first API interaction (`POST /initialize { client_id: "cli_xxx" }`) so Bill knows who he's talking to immediately
- User never sees the login screen again unless they clear data or use a new device
- Optional: "Not you?" link on home screen to switch accounts / return to login

#### Device Recognition Flow

```
App loads
  → Check localStorage for client_id
  → IF found:
      → POST /initialize { client_id: stored_id }
      → Backend confirms identity, returns context
      → Navigate to #/home (skip login)
  → IF not found:
      → Show login screen (#/login)
      → User enters Client ID or starts new registration
      → On success: store client_id in localStorage
      → Navigate to #/home
```

---

### 1. Home Screen (`#/home`)

The primary hub. Three sections stacked vertically:

#### Section A: Progress Snapshot (top)

Compact card showing:
- **Sessions completed** (this training block)
- **Current phase/week** (e.g. "Strength Foundation — Week 4")
- **Recent PBs** (if any in last 7 days, show 1-2 lines — exercise name + value)

Data source: Client context from backend `/initialize` or cached from last load.

#### Section B: Next Session Card

Compact card showing:
- **Session day/date** (e.g. "Tuesday 18 Feb")
- **Session summary** — the pre-written `session_summary` field from `plan_sessions` table
- **"Start Session" button** — navigates to session preview

If no upcoming session: show rest day message.
If session is today: visually emphasise the card (brighter border, "TODAY" badge).

#### Section C: Chat with Bill (fills remaining space)

- Chat message area (scrollable, newest at bottom)
- Bill's messages: small circular portrait avatar on the left, message bubble on the right
- User's messages: right-aligned bubbles, no avatar
- **Chat input pinned to bottom of viewport** (fixed position)
  - Text input field + send button
  - Input should not be obscured by mobile keyboard (scroll into view)
- Chat history persisted in localStorage between visits
- Typing indicator while waiting for Bill's response

#### Home Screen Layout (Mobile)

```
┌─────────────────────────────┐
│ [Progress Snapshot Card]    │
│ Sessions: 47 | Week 4       │
│ PB: Squat 110kg x 5        │
├─────────────────────────────┤
│ [Next Session Card]         │
│ Tue 18 Feb — TODAY          │
│ "Lower body strength focus  │
│  with posterior chain..."    │
│ [  Start Session  ]         │
├─────────────────────────────┤
│                             │
│ 🟤 Bill: Right then, how    │
│    are you feeling today?   │
│                             │
│         Feeling good,  :You │
│         ready to go!        │
│                             │
│ 🟤 Bill: Excellent. Today's │
│    session hits legs hard... │
│                             │
│ (scrollable)                │
├─────────────────────────────┤
│ [Type a message...]  [Send] │ ← pinned to bottom
└─────────────────────────────┘
```

---

### 2. Session Preview (`#/session-preview/{session_id}`)

Read-only overview before committing to the workout. Navigated to from "Start Session" on home screen.

- **Back button** (top-left, returns to home)
- **Session header**: phase, focus, location, duration, intensity
- **Exercise list** grouped by segment (warm-up / main / cool-down)
  - Each exercise shown as a compact card: name + prescription summary (e.g. "4 x 6 @ 100kg")
  - Colour-coded left border per segment (blue/warm-up, orange/main, green/cool-down)
- **Equipment needed** (derived from exercise data)
- **"BEGIN WORKOUT" button** (fixed at bottom)
  - On tap: auto-logs session start timestamp, navigates to active session

---

### 3. Active Session (`#/session-active/{session_id}`)

The core workout logging experience. Full-screen, focused.

#### Overall Structure

- **Segment tabs/headers**: Warm-up → Main → Cool-down
- Each segment shows **all its steps as a collapsed list**
- User taps any step to expand it (accordion pattern)
- **User controls the order** — especially in Main, where equipment availability dictates sequence

#### Collapsed Step (list item)

```
┌─────────────────────────────┐
│ ● Barbell Back Squat        │
│   4 × 6 @ 100kg            │
│                    [expand] │
└─────────────────────────────┘
```

Shows: exercise name, prescription summary, completion status (empty circle → tick when done).

#### Expanded Step (detail + data entry)

```
┌──────────────────────────────────┐
│ ▼ Barbell Back Squat             │
│   4 × 6 @ 100kg | RPE 8         │
│                                  │
│ Coach note: "Control the         │
│ descent, explode up. Leave       │
│ 2 reps in tank."                 │
│                                  │
│ [▶ Video]  [ℹ Details]          │
│                                  │
│ Tempo: 3-0-1-0                   │
│ Rest: 180s                       │
│                                  │
│        Reps      kg              │
│ Set 1: [___6___] [__100__]       │
│ Set 2: [___6___] [__100__]       │
│ Set 3: [___6___] [__100__]       │
│ Set 4: [___6___] [__100__]       │
│ Set 5: [_______] [_______]       │
│                                  │
│ Exercise RPE: [  /10  ]          │
│ Notes: [_______________________] │
│                                  │
│ [  Mark Complete  ]              │
└──────────────────────────────────┘
```

- **Video link**: opens YouTube in new tab/overlay
- **Details**: expandable long description from Exercise Library
- **Input fields — up to 5 sets per exercise**:
  - Number of set rows shown = prescribed sets (e.g. 4), but always allow up to 5 (extra row available if user wants a bonus set)
  - Pre-filled with prescribed values (reps + load) as default values, user overwrites with actuals
  - **Dynamic measure unit** — the second input column label is determined by the exercise type from the Exercise Library:
    - Weighted exercises → **kg** (e.g. Barbell Back Squat)
    - Timed exercises → **seconds** (e.g. Plank hold)
    - Distance exercises → **km** or **m** (e.g. Running, Rowing)
    - Bodyweight rep exercises → reps only, no second column (e.g. Push-ups)
  - The unit label displays above the column so the user always knows what they're entering
  - Number inputs with large tap targets (mobile keyboard: numeric)
  - Empty/unused set rows are visually dimmed but tappable
- **Exercise RPE**: 1-10 scale (tap to select)
- **Notes**: free text field for that exercise
- **Mark Complete**: collapses the step back, shows tick, saves to localStorage draft

#### Session Completion

When all steps are marked complete (or user decides to finish early):
- **"Complete Session" button** appears
- **Overall session RPE** entry (1-10)
- **Session notes** field
- On submit:
  - Auto-log session end timestamp
  - POST all logged data to backend
  - Navigate to session complete view

#### Draft Saving

- Auto-save all input to localStorage every 30 seconds
- Restore draft on page reload (if session not yet submitted)
- Visual indicator: "Draft saved" timestamp

---

### 4. Session Complete (`#/session-complete/{session_id}`)

Post-workout summary. Brief, rewarding.

- **Session summary**: duration (start → end), exercises completed count
- **PBs achieved** (if any — highlighted prominently)
- **Bill's response**: a short coaching message about the session (from chat API or pre-generated)
- **"Back to Home" button**

---

### 5. Progress & History (`#/progress`) — FUTURE / LOW PRIORITY

Not in initial build scope. Placeholder view with "Coming soon" message.
Bill can answer progress questions in chat for now.

---

## Visual Design System

### Colour Palette (Dark & Warm)

```css
:root {
  /* Primary */
  --bill-primary: #d2691e;        /* Chocolate — buttons, accents */
  --bill-primary-dark: #a0522d;   /* Sienna — hover states */
  --bill-primary-light: #e89b5e;  /* Light chocolate — highlights */

  /* Neutrals */
  --bill-bg-dark: #2a2a2a;        /* Charcoal — page background */
  --bill-bg-darker: #1a1a1a;      /* Deep charcoal — inset areas */
  --bill-bg-card: #363636;        /* Card background */
  --bill-bg-input: #2e2e2e;       /* Input field background */

  /* Text */
  --bill-text-primary: #f5f5f5;   /* Primary text */
  --bill-text-muted: #b0b0b0;     /* Secondary text */
  --bill-text-accent: #f5deb3;    /* Wheat — headings, emphasis */

  /* Semantic */
  --bill-success: #4a7c2d;        /* Olive green — completed */
  --bill-warning: #d4a520;        /* Goldenrod — attention */
  --bill-danger: #c84b4b;         /* Red — errors, injuries */

  /* Segment colours */
  --segment-warmup: #4a9eff;      /* Blue */
  --segment-main: #ff8c42;        /* Orange */
  --segment-cooldown: #4a7c2d;    /* Green */
}
```

### Typography

- **Headings**: Georgia / serif — gives the Victorian character feel
- **Body**: System sans-serif stack — clean, readable, fast
- **Base size**: 16px, scale up for touch targets
- **Line height**: 1.6 for body, 1.2 for headings

### Component Patterns

- **Cards**: `#363636` background, 12px radius, subtle brown-tinted border (`rgba(210,105,30,0.2)`), soft shadow
- **Buttons (primary)**: Chocolate background, white text, 8px radius, min height 48px (touch target)
- **Buttons (secondary)**: Transparent background, chocolate border, chocolate text (dark-theme friendly — NOT white background)
- **Inputs**: Dark background (`#2e2e2e`), subtle border, wheat-coloured focus ring, min height 48px
- **Exercise cards**: Left colour-border by segment type, expandable accordion
- **Chat bubbles**: Bill's messages left-aligned with avatar, user's right-aligned. Distinct bubble colours.
- **Badges**: Small pill shapes for segment labels, status indicators

### Touch Targets

All interactive elements: **minimum 48x48px** tap area (Google Material Design guideline).
Number inputs in session logging: **extra large** — easy to tap with sweaty gym hands.

### Responsive Breakpoints

```
Mobile:   < 640px   — single column, full-width cards
Tablet:   640-1024px — slightly wider container, more breathing room
Desktop:  > 1024px  — max-width container (640px), centred, optional side panels
```

---

## Data Flow

### App Launch (Login / Recognition)

```
1. App initialises → check localStorage for client_id
2. IF client_id found:
     → POST /initialize { client_id } (Bill knows who this is)
     → Skip login, go straight to #/home
3. IF not found:
     → Show #/login screen (large Bill portrait, Client ID input)
     → User enters existing ID or starts fresh (Bill onboards via chat)
     → On success: store client_id in localStorage
     → Navigate to #/home
```

### Home Screen Load

```
1. Client context available from /initialize response (or cached)
2. Render progress snapshot from client context
3. Render next session card using session_summary field
4. Load chat history from localStorage
5. Chat ready for new messages via POST /chat
```

### Session Start

```
1. User taps "Start Session" on home or preview
2. Auto-log: session_start_timestamp = now()
3. GET /sessions/{id}/steps → load all steps
4. Render active session view (warm-up segment first)
5. Auto-save draft to localStorage on input changes
```

### Session Submit

```
1. User taps "Complete Session"
2. Auto-log: session_end_timestamp = now()
3. Collect all step data + session RPE + notes
4. POST /sessions/{id}/complete → backend → Make.com session_update webhook
5. Clear draft from localStorage
6. Show session complete view
7. Backend triggers Exercise Bests recalculation (async)
```

---

## Build Phases (Suggested Order)

### Phase 1: SPA Shell + Login + Home Screen (Foundation)

- [ ] Create SPA shell (`index.html` with `<div id="app">`, hash router)
- [ ] Implement view lifecycle (render/destroy pattern)
- [ ] Strip Tailwind CDN, consolidate into `app.css`
- [ ] Fix secondary button styles for dark theme (no white backgrounds)
- [ ] Build login screen: large Bill portrait, Client ID input, new user path
- [ ] Device recognition: localStorage check → auto-skip login for returning users
- [ ] Pass stored `client_id` to backend on first API call (`POST /initialize`)
- [ ] Build home screen layout: progress card + session summary card + chat area
- [ ] Chat UI: message bubbles, Bill's avatar, pinned input, typing indicator
- [ ] Chat functionality: send/receive via API, localStorage history
- [ ] Mock data integration for all home screen components

### Phase 2: Session Preview

- [ ] Session preview view with exercise list by segment
- [ ] Colour-coded segment cards (warm-up/main/cool-down)
- [ ] Equipment list derived from exercise data
- [ ] "BEGIN WORKOUT" button with timestamp auto-log

### Phase 3: Active Session (Core MVP)

- [ ] Segment-grouped exercise list (collapsed view)
- [ ] Accordion expand/collapse on tap
- [ ] Exercise detail panel: coach notes, video link, description
- [ ] Data entry inputs: up to 5 sets per exercise, prescribed sets pre-filled
- [ ] Dynamic measure unit per exercise (kg / seconds / km / m) from Exercise Library
- [ ] Unit label displayed above input column
- [ ] Exercise RPE + notes per step
- [ ] Mark step complete
- [ ] User-controlled exercise order (especially in Main)
- [ ] Draft auto-save to localStorage
- [ ] Draft restore on reload

### Phase 4: Session Completion

- [ ] Session completion flow: overall RPE + notes
- [ ] Auto-log end timestamp
- [ ] POST submission to backend
- [ ] Session complete summary view
- [ ] PB detection display
- [ ] Clear draft on successful submit

### Phase 5: Polish & PWA

- [ ] Optimise Bill's portrait (<50KB, consider WebP)
- [ ] Generate PWA icons (192x192, 512x512)
- [ ] Service worker: cache static assets, offline fallback page
- [ ] Loading states (skeleton screens, not just spinners)
- [ ] Error states (connection failed, session expired)
- [ ] Mobile keyboard handling (chat input, number inputs)
- [ ] Test on iOS Safari + Android Chrome
- [ ] Desktop layout adjustments (centred container, breathing room)

### Phase 6: Future (Out of Scope)

- [ ] Progress & history view
- [ ] Offline session logging (queue submissions)
- [ ] Push notifications (session reminders)
- [ ] Dark/light theme toggle
- [ ] Enhanced onboarding flow (guided walkthrough beyond basic login)

---

## Key Constraints

1. **No build tools required** — vanilla JS, no bundler, no npm. Keep it simple.
2. **Backend is being developed in parallel** — use mock data until endpoints are ready.
3. **Session summary comes from backend** — the `session_summary` field in `plan_sessions` is pre-written by Bill during training week generation. No client-side summarisation.
4. **Webhook payloads are execution law** — frontend must match the exact schema the backend/Make.com expects.
5. **ADHD-friendly dev workflow** — small chunks, verify each step, skeleton first.

---

## Files to Remove/Replace

- All current `.html` files except `index.html` (becomes the SPA shell)
- Current `dashboard.html`, `session-preview.html` become JS view modules
- Tailwind CDN `<script>` tags removed from all files
- Fix all hardcoded light-theme Tailwind classes in JS (`bg-gray-50`, `text-gray-900`, `bg-white`)

---

**Next Step:** Review this document, then begin Phase 1 (SPA shell + home screen).
