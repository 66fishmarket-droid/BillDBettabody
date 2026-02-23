// Bill D'Bettabody - Week View

const STATUS_LABEL = {
  'awaiting content': '',
  'scheduled': '',
  'completed': '✓ Done',
  'skipped': 'Skipped',
};

const DAY_ABBR = {
  Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed', Thursday: 'Thu',
  Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun',
};

class WeekView {
  constructor() {
    this.data = null;
  }

  async init() {
    await app.init();

    document.getElementById('back-btn').addEventListener('click', () => {
      window.location.href = '/dashboard.html';
    });

    if (!app.sessionId) {
      window.location.href = '/index.html';
      return;
    }

    await this.load();
  }

  async load() {
    try {
      app.showLoading('Loading your week...');
      this.data = await api.getWeek(app.sessionId);
      app.hideLoading();
      this.render();
    } catch (err) {
      app.hideLoading();
      console.error('[Week] Load failed:', err);
      app.showError('Could not load week data. Please try again.');
    }
  }

  render() {
    const sessions = (this.data && this.data.sessions) || [];

    // Subtitle
    const subtitleEl = document.getElementById('week-subtitle');
    if (subtitleEl && this.data) {
      const parts = [];
      if (this.data.phase_name) parts.push(this.data.phase_name);
      if (this.data.week_number) parts.push(`Week ${this.data.week_number}`);
      subtitleEl.textContent = parts.join(' · ');
    }

    if (!sessions.length) {
      document.getElementById('week-empty').hidden = false;
      return;
    }

    const container = document.getElementById('week-container');
    container.innerHTML = sessions.map((s, idx) => this.renderSession(s, idx)).join('');

    // Attach click listeners after DOM update
    container.querySelectorAll('.week-session-card').forEach(card => {
      card.addEventListener('click', () => {
        const idx = parseInt(card.dataset.idx, 10);
        this.openSession(idx);
      });
    });
  }

  renderSession(s, idx) {
    const dayLabel  = DAY_ABBR[s.day_of_week] || s.day_of_week || '';
    const focus     = s.focus || 'Training Session';
    const location  = s.location ? `<span style="font-size:0.8rem;color:#b0b0b0;">📍 ${this.cap(s.location)}</span>` : '';
    const duration  = s.estimated_duration ? `<span style="font-size:0.8rem;color:#b0b0b0;">⏱ ${s.estimated_duration} min</span>` : '';
    const rpe       = s.intended_intensity_rpe ? `<span style="font-size:0.8rem;color:#b0b0b0;">RPE ${s.intended_intensity_rpe}</span>` : '';

    const status    = (s.status || '').toLowerCase();
    const isDone    = status === 'completed';
    const statusTag = STATUS_LABEL[status]
      ? `<span style="font-size:0.75rem;color:${isDone ? '#b0b0b0' : '#e89b5e'};margin-left:auto;">${STATUS_LABEL[status]}</span>`
      : '';

    const exercises = (s.exercises || []).length
      ? `<div style="margin-top:0.5rem;">
           <p style="font-size:0.75rem;color:#b0b0b0;margin-bottom:0.25rem;">Main exercises:</p>
           <p style="font-size:0.875rem;color:#e0e0e0;">${s.exercises.map(e => this.esc(e)).join(', ')}</p>
         </div>`
      : '';

    const summary = s.session_summary
      ? `<p style="font-size:0.8rem;color:#b0b0b0;margin-top:0.25rem;">${this.esc(s.session_summary)}</p>`
      : '';

    return `
      <div class="card mb-3 week-session-card"
           data-idx="${idx}"
           style="${isDone ? 'opacity:0.6;' : ''}cursor:pointer;"
      >
        <div style="display:flex;align-items:flex-start;gap:0.75rem;">
          <div style="min-width:2.75rem;text-align:center;background:#fef3c7;border-radius:0.5rem;padding:0.35rem 0.25rem;">
            <div style="font-size:0.7rem;font-weight:600;color:#92400e;text-transform:uppercase;">${this.esc(dayLabel)}</div>
            <div style="font-size:1rem;font-weight:700;color:#78350f;line-height:1.2;">${this.dayNum(s.session_date)}</div>
          </div>
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
              <span style="font-weight:600;font-size:0.95rem;color:#f5f5f5;">${this.esc(focus)}</span>
              ${statusTag}
            </div>
            ${summary}
            <div style="display:flex;gap:0.75rem;margin-top:0.35rem;flex-wrap:wrap;">
              ${location}${duration}${rpe}
            </div>
            ${exercises}
          </div>
          <div style="font-size:1rem;color:#b0b0b0;align-self:center;">›</div>
        </div>
      </div>
    `;
  }

  openSession(idx) {
    const sessions = (this.data && this.data.sessions) || [];
    const s = sessions[idx];
    if (!s) return;
    app.setActiveSession(s);
    window.location.href = '/session-preview.html';
  }

  formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    } catch { return dateStr; }
  }

  dayNum(dateStr) {
    if (!dateStr) return '';
    try { return new Date(dateStr + 'T00:00:00').getDate(); }
    catch { return ''; }
  }

  cap(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

const weekView = new WeekView();
document.addEventListener('DOMContentLoaded', () => weekView.init());
