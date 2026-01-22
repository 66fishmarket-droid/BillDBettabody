# Bill D'Bettabody - PWA Frontend

**Status:** MVP v1 - Today Screen Complete with Mock Data

## What's Built

### ✅ Complete
- **Project structure** - organized, scalable file layout
- **PWA basics** - manifest.json, service worker (installable)
- **Mock data** - realistic data matching your Google Sheets schema
- **API wrapper** - ready to swap mock → real backend
- **Core app logic** - session management, navigation
- **Today screen (Dashboard)** - main landing page with:
  - Client summary (sessions completed, current phase)
  - Today's session card (focus, location, duration, intensity, exercise breakdown)
  - Daily nutrition targets
  - "Talk to Bill" button
  - "Start Session" button
- **Custom styling** - Bill's gruff-but-warm Victorian aesthetic

### 🚧 In Progress
- Session preview screen
- Active session flow
- Progress view
- Chat interface

---

## How to Test

### Option 1: Simple HTTP Server (Python)

```bash
cd bill-pwa
python3 -m http.server 8000
```

Then open: `http://localhost:8000`

### Option 2: VS Code Live Server

1. Install "Live Server" extension in VS Code
2. Right-click `index.html`
3. Select "Open with Live Server"

### Option 3: Any HTTP Server

```bash
# Node.js http-server
npx http-server -p 8000

# PHP
php -S localhost:8000
```

---

## Testing on Mobile

### Option A: Ngrok (Easiest for remote testing)

```bash
# Start local server first
python3 -m http.server 8000

# In another terminal
ngrok http 8000
```

You'll get a public HTTPS URL you can open on your phone.

### Option B: Local Network

1. Start server: `python3 -m http.server 8000`
2. Find your computer's IP: `ifconfig` (Mac/Linux) or `ipconfig` (Windows)
3. On your phone, open: `http://YOUR_IP:8000`

---

## Current Mock Data

The app uses realistic mock data in `/js/mock-data.js`:

- **Client:** Demo User, 35M, 82kg, 47 sessions completed
- **Today's Session:** Lower Body Strength (Tue, 21 Jan 2026)
  - 4 warmup exercises
  - 5 main exercises (squat, RDL, Bulgarian split squat, leg curl, calf raise)
  - 3 cooldown exercises
- **Nutrition:** 2400 cal, 180g protein
- **Bests:** Back squat 125kg e1RM, RDL 105kg e1RM

---

## Next Steps

### Immediate (Today)
1. **Session Preview Screen** - pre-workout overview with all exercise names
2. **Active Session Flow** - exercise-by-exercise logging

### Soon
3. **Post-Session Completion** - RPE, reflections, pain flags
4. **Progress View** - exercise bests, category groupings
5. **Chat Interface** - talk to Bill

### Backend Integration
Once screens are built with mock data:
1. Add 6 backend endpoints (GET today, steps, bests, etc.)
2. Change `API_CONFIG.USE_MOCK_DATA = false` in `/js/api.js`
3. Set `API_CONFIG.BASE_URL` to your backend URL
4. Test with real data

---

## File Structure

```
bill-pwa/
├── index.html              # Entry point (simple for now)
├── dashboard.html          # Today screen ✅
├── session-preview.html    # 🚧 Next
├── session-active.html     # 🚧 After that
├── progress.html           # 🚧 Future
├── chat.html               # 🚧 Future
│
├── css/
│   └── app.css             # Bill's custom styles ✅
│
├── js/
│   ├── app.js              # Core app logic ✅
│   ├── api.js              # Backend wrapper ✅
│   ├── mock-data.js        # Fake data ✅
│   ├── dashboard.js        # Today screen logic ✅
│   ├── session.js          # 🚧 Active session logic
│   └── progress.js         # 🚧 Progress charts
│
├── manifest.json           # PWA manifest ✅
├── sw.js                   # Service worker ✅
└── assets/
    └── icons/              # App icons (need to add)
```

---

## Design Notes

### Bill's Aesthetic
- **Colors:** Earthy browns, warm beige background
- **Typography:** Georgia for headings (Victorian feel), system font for body
- **Tone:** Gruff but warm - no-nonsense but caring
- **Mobile-first:** Everything designed for phone use

### Data Flow
```
Mock Data → API Wrapper → Dashboard
(swap mock for real backend when ready)
```

---

## Known Issues / TODO

- [ ] Add app icons (192x192, 512x512)
- [ ] Build remaining screens (preview, active, progress, chat)
- [ ] Add real error handling (currently just alerts)
- [ ] Add offline support to service worker (currently just installability)
- [ ] Add session state persistence (if user closes app mid-session)

---

## Questions?

Slack me or shout in the project channel.

**Next:** Session Preview screen - do you want to review the Today screen first or should I keep building?
