const BILL_MESSAGES = [
  "That's the work done. Session logged. Bill approves.",
  "Consistency beats perfection. You showed up — that's what counts.",
  "Every rep is a vote for the person you're becoming.",
  "Logged and locked in. Rest up, recover well.",
  "The work is done. Now let it sink in.",
  "No shortcuts, no excuses. That's your character showing.",
  "Champions don't skip. You just proved you're not a skipper.",
];

function init() {
  const raw = localStorage.getItem('bill_session_summary');
  let summary = null;
  try {
    summary = raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[Session Complete] Could not parse summary:', e);
  }

  // Subheading: focus · date
  const focusEl = document.getElementById('complete-focus');
  if (summary) {
    const parts = [summary.focus, summary.session_date].filter(Boolean);
    focusEl.textContent = parts.join(' · ');
  } else {
    focusEl.textContent = 'Great work today';
  }

  // Stats row
  const stats = [];
  const exerciseCount = summary?.main_exercises?.length ?? 0;
  stats.push({ value: exerciseCount, label: exerciseCount === 1 ? 'Exercise' : 'Exercises' });
  if (summary?.rpe) {
    stats.push({ value: `${summary.rpe}/10`, label: 'Session RPE' });
  }
  if (summary?.location) {
    stats.push({ value: summary.location, label: 'Location' });
  }

  document.getElementById('complete-stats').innerHTML = stats.map(s => `
    <div class="stat-item">
      <span class="stat-value">${s.value}</span>
      <span class="stat-label">${s.label}</span>
    </div>
  `).join('');

  // Exercise list
  const exercises = summary?.main_exercises ?? [];
  if (exercises.length) {
    document.getElementById('complete-exercise-list').innerHTML =
      exercises.map(name => `<li>${name}</li>`).join('');
  } else {
    document.getElementById('complete-exercises-card').hidden = true;
  }

  // Motivational quote
  document.getElementById('complete-quote').textContent =
    BILL_MESSAGES[Math.floor(Math.random() * BILL_MESSAGES.length)];

  // Back to dashboard — clear summary so it doesn't linger
  document.getElementById('back-to-dashboard-btn').addEventListener('click', () => {
    localStorage.removeItem('bill_session_summary');
    window.location.href = '/dashboard.html';
  });
}

document.addEventListener('DOMContentLoaded', init);
