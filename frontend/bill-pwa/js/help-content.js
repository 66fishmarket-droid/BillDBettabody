// ─── Help / FAQ content ───────────────────────────────────────────────────
// One entry per page. Add or edit FAQs here — no other file needs changing.
// Each FAQ: { q: 'Question text', a: 'Answer text' }
// 'a' supports basic HTML (e.g. <strong>, <br>).

const HELP_CONTENT = {

  dashboard: {
    title: 'Using the Dashboard',
    faqs: [
      {
        q: 'How do I start today\'s session?',
        a: 'Tap <strong>Start Session</strong> on the Today\'s Session card. You\'ll see a preview of the full workout before it begins.'
      },
      {
        q: 'What do the stats on my Progress card mean?',
        a: '<strong>Sessions Done</strong> is your total logged sessions. The second stat shows which week of your current training block you\'re in.'
      },
      {
        q: 'What are my Daily Targets?',
        a: 'These are your personalised nutrition targets — calories and protein — set by Bill based on your goals. Supplements listed below are your current protocol.'
      },
      {
        q: 'How do I talk to Bill?',
        a: 'Tap <strong>💬 Talk to Bill</strong> to open a chat. Bill can answer questions about your training, nutrition, upcoming sessions, or how to work around an injury.'
      },
      {
        q: 'Can I change my training plan?',
        a: 'Yes — ask Bill in chat. He can discuss adjustments, explain why something is programmed, and pass change requests through to your coach.'
      },
      {
        q: 'What if there\'s no session showing today?',
        a: 'It\'s a rest day, or your programme hasn\'t been set up yet. Tap <strong>📅 This Week</strong> to see your full week\'s schedule, or ask Bill.'
      }
    ]
  },

  'session-preview': {
    title: 'Reading Your Session',
    faqs: [
      {
        q: 'What are the three sections (Warm-up, Main Work, Cool-down)?',
        a: 'Every session is structured into three segments. <strong>Warm-up</strong> prepares your body. <strong>Main Work</strong> is the core training. <strong>Cool-down</strong> aids recovery. Each shows its exercises and estimated duration.'
      },
      {
        q: 'How do I see details about an exercise?',
        a: 'Tap any exercise card to open its detail panel — you\'ll see the full description, coaching cues, video, safety notes, and easier or harder alternatives.'
      },
      {
        q: 'What does the equipment list mean?',
        a: 'Everything you\'ll need for the full session, listed upfront so you can set up before you start. Check this before heading to the gym floor.'
      },
      {
        q: 'What do sets × reps mean?',
        a: '<strong>Sets</strong> is how many times you do the block of work. <strong>Reps</strong> is how many repetitions per set. For example, 4 × 8 means 4 sets of 8 reps each.'
      },
      {
        q: 'What is tempo (e.g. 3010)?',
        a: 'Four digits: <strong>seconds lowering · pause at bottom · seconds lifting · pause at top</strong>. So 3010 means 3 seconds down, no pause, 1 second up, no pause at the top.'
      },
      {
        q: 'Can I ask Bill about a specific exercise before I start?',
        a: 'Yes — tap the exercise card to open details, then tap <strong>💬 Ask Bill</strong>. Or open chat directly and mention the exercise name.'
      }
    ]
  },

  'session-active': {
    title: 'Logging Your Session',
    faqs: [
      {
        q: 'How do I log a set?',
        a: 'Each exercise card has input fields for weight and reps. Fill them in after completing the set, then tap <strong>+ Add Set</strong>. Repeat for each set.'
      },
      {
        q: 'What is RPE?',
        a: 'RPE (Rate of Perceived Exertion) is a 1–10 scale of effort. <strong>6</strong> = comfortable. <strong>8</strong> = hard but manageable. <strong>10</strong> = maximum. Log the RPE that matches how the set actually felt, not how it was supposed to feel.'
      },
      {
        q: 'What does tempo mean (e.g. 3010)?',
        a: 'Four digits: <strong>seconds lowering · pause at bottom · seconds lifting · pause at top</strong>. 3010 = 3s down, no pause, 1s up, no pause at top. Use a mental count — it doesn\'t need to be exact.'
      },
      {
        q: 'What if I can\'t do an exercise?',
        a: 'Tap <strong>📖 Details</strong> on the exercise to see the Easier Option (regression). If you need more guidance, tap <strong>💬 Ask Bill</strong> — he can suggest alternatives based on your situation.'
      },
      {
        q: 'How do I see exercise instructions mid-session?',
        a: 'Tap <strong>📖 Details</strong> on any exercise card to open the full description, coaching cues, video, and safety notes without leaving the session.'
      },
      {
        q: 'What does the Terms glossary cover?',
        a: 'Tap <strong>📖 Terms</strong> in the header to open a quick reference for training jargon — RPE, tempo, loading patterns, and rep schemes.'
      },
      {
        q: 'How do I finish the session?',
        a: 'Complete your exercises, then scroll to the bottom. Rate your overall session RPE (1–10), add any notes, and tap <strong>Complete Session</strong>.'
      },
      {
        q: 'Do I have to log every set?',
        a: 'You don\'t have to, but it helps Bill track your progress and adjust future sessions. At minimum, log anything that felt significantly harder or easier than expected.'
      }
    ]
  },

  'session-complete': {
    title: 'Session Complete',
    faqs: [
      {
        q: 'Is my session saved?',
        a: 'Yes — as soon as you tapped Complete Session, your data was saved. The stats shown here confirm what was logged.'
      },
      {
        q: 'What happens to my data?',
        a: 'Your session results are used by Bill to track progress over time, adjust future programming, and show your improvement trends in the Progress view.'
      },
      {
        q: 'What if I made a mistake in my logging?',
        a: 'Ask Bill in chat — he can look at your recent session data and note any corrections for your coach to review.'
      }
    ]
  },

  progress: {
    title: 'Your Progress',
    faqs: [
      {
        q: 'What are the progress groups?',
        a: 'Exercises are grouped by movement pattern — e.g. <strong>Upper Push</strong>, <strong>Lower Body</strong>, <strong>Distance</strong>. Each group shows your performance trend across sessions.'
      },
      {
        q: 'What does % improvement mean?',
        a: 'The percentage change from your first recorded performance for that movement pattern to your current personal best. Positive = you\'re getting stronger or fitter.'
      },
      {
        q: 'Why is a group not showing?',
        a: 'A group only appears once you have at least two logged sessions with exercises in that category. Keep logging and it will populate.'
      },
      {
        q: 'Can I see progress for a specific exercise?',
        a: 'Not yet at the individual exercise level — this view tracks movement patterns. Ask Bill in chat if you want to discuss a specific lift\'s trend.'
      }
    ]
  },

  week: {
    title: 'This Week\'s Schedule',
    faqs: [
      {
        q: 'What does this view show?',
        a: 'Your full week of planned sessions — each card shows the day, session focus, and estimated duration. Tap a session to go to its preview.'
      },
      {
        q: 'What if a session is missing?',
        a: 'It may be a rest day, or the session hasn\'t been added to your programme yet. Ask Bill if you think something is missing.'
      },
      {
        q: 'Can I do sessions in a different order?',
        a: 'Ask Bill — he can advise on whether swapping days affects your recovery or training goals.'
      }
    ]
  },

  chat: {
    title: 'Talking to Bill',
    faqs: [
      {
        q: 'What can I ask Bill?',
        a: 'Anything about your training — exercise technique, plan adjustments, nutrition questions, how to work around pain or injury, what a result means, or what to focus on next.'
      },
      {
        q: 'Can Bill change my training plan?',
        a: 'Bill can discuss and process changes. Some adjustments happen automatically. Others are flagged for coach review. Either way, Bill will tell you what\'s happening.'
      },
      {
        q: 'How do I ask about a specific exercise?',
        a: 'Just name it — <em>"How do I do a Romanian Deadlift?"</em> or <em>"Is there an easier version of Bulgarian Split Squats?"</em> Bill knows the full exercise library.'
      },
      {
        q: 'How do I ask for a new feature or change to the app?',
        a: 'Tell Bill what you\'d like to be able to do and he\'ll pass it on. You can also be specific — <em>"I\'d like to be able to log cardio time"</em> is more useful than <em>"the app needs more features"</em>.'
      },
      {
        q: 'What if Bill gives a wrong or confusing answer?',
        a: 'Tell him — <em>"That doesn\'t seem right"</em> or <em>"Can you explain that differently?"</em> works well. For anything health-critical, always defer to your coach or medical professional.'
      }
    ]
  }

};
