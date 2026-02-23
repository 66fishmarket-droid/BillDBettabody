// Bill D'Bettabody - Dashboard Logic
// Today screen functionality

class Dashboard {
  constructor() {
    this.dashboard = null;
    this.restSummary = null;
    this.profile = null;
    this.completedSummary = null;  // set when user just finished a session
  }

  async init() {
    console.log('[Dashboard] Initializing...');

    try {
      app.showLoading('Loading your day...');

      if (!app.sessionId) {
        console.warn('[Dashboard] No session found. Redirecting to login.');
        window.location.href = '/index.html';
        return;
      }

      // Check if the user just completed a session (set by session-active.js)
      const raw = localStorage.getItem('bill_session_summary');
      if (raw) {
        try { this.completedSummary = JSON.parse(raw); } catch (_) {}
        localStorage.removeItem('bill_session_summary');
      }

      // Load dashboard + profile
      await Promise.all([
        this.loadDashboard(),
        this.loadProfile()
      ]);

      // Render the dashboard
      this.render();

      // Setup event listeners
      this.setupEventListeners();

      app.hideLoading();
    } catch (error) {
      console.error('[Dashboard] Initialization failed:', error);
      app.hideLoading();
      app.showError('Failed to load dashboard. Please refresh.');
    }
  }

  async loadDashboard() {
    this.dashboard = await api.getDashboard(app.sessionId);
    console.log('[Dashboard] Dashboard loaded:', this.dashboard);

    if (!this.dashboard || !this.dashboard.next_session) {
      try {
        const rest = await api.getRestDaySummary(app.sessionId);
        this.restSummary = rest && rest.summary ? rest.summary : null;
      } catch (error) {
        console.warn('[Dashboard] Rest day summary failed:', error);
      }
    }
  }

  async loadProfile() {
    try {
      this.profile = await api.getProfile(app.sessionId);
      console.log('[Dashboard] Profile loaded:', this.profile);
    } catch (error) {
      console.warn('[Dashboard] Profile load failed:', error);
      this.profile = null;
    }
  }

  render() {
    // Date
    const dateEl = document.getElementById('today-date');
    if (dateEl) {
      const today = new Date();
      const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
      dateEl.textContent = today.toLocaleDateString('en-GB', options);
    }

    // Client summary
    const nameEl = document.getElementById('client-name');
    if (nameEl) {
      if (this.profile && (this.profile.first_name || this.profile.last_name)) {
        nameEl.textContent = `${this.profile.first_name || ''} ${this.profile.last_name || ''}`.trim();
      } else {
        nameEl.textContent = app.clientId ? `Client: ${app.clientId}` : 'Client';
      }
    }

    const sessionsEl = document.getElementById('sessions-completed');
    if (sessionsEl) {
      const completed = (this.dashboard && this.dashboard.completed_sessions != null)
        ? this.dashboard.completed_sessions
        : (this.profile && this.profile.completed_sessions) || 0;
      sessionsEl.textContent = completed;
    }

    const weekEl = document.getElementById('current-week');
    const phaseEl = document.getElementById('current-phase');
    if (weekEl) {
      const block = this.dashboard ? this.dashboard.block_summary : null;
      weekEl.textContent = block && block.week_number
        ? `Week ${block.week_number}`
        : 'Starting soon';
      if (phaseEl) {
        phaseEl.textContent = (block && block.phase_name)
          ? block.phase_name
          : 'Current Phase';
      }
    }

    // Today's session card
    const nextSession = this.dashboard && this.dashboard.next_session;
    const todayStr = new Date().toISOString().split('T')[0]; // YYYY-MM-DD local
    const sessionIsToday = nextSession && nextSession.session_date === todayStr;

    if (this.completedSummary) {
      this.renderSessionComplete(this.completedSummary);
    } else if (sessionIsToday) {
      this.renderSession(this.dashboard);
    } else if (nextSession) {
      // Today is a rest day — show rest day message + upcoming session preview
      this.renderRestDay(nextSession);
    } else {
      this.renderNoSession();
    }

    // Nutrition targets from Plans_Blocks
    const nt = this.dashboard && this.dashboard.nutrition_targets;
    const caloriesEl = document.getElementById('calories-target');
    if (caloriesEl) {
      caloriesEl.textContent = (nt && nt.calories) ? nt.calories : '—';
    }

    const proteinEl = document.getElementById('protein-target');
    if (proteinEl) {
      proteinEl.textContent = (nt && nt.protein) ? `${nt.protein}g` : '—';
    }

    // Supplement protocol from Plans_Blocks
    const supplements = this.dashboard && this.dashboard.supplement_protocol;
    const suppList = document.getElementById('supplement-list');
    if (suppList && supplements && supplements.length) {
      suppList.innerHTML = supplements.map(s =>
        `<li><strong>${s.name}</strong> — ${s.dosage}${s.timing ? `, ${s.timing}` : ''}</li>`
      ).join('');
      suppList.hidden = false;
    }
  }

  renderSession(sessionData) {
    const session = sessionData.next_session;

    // Session focus
    const focusEl = document.getElementById('session-focus');
    if (focusEl) {
      focusEl.textContent = session.focus || 'Training Session';
    }

    // Session details
    const detailsEl = document.getElementById('session-details');
    if (detailsEl) {
      const summaryBlock = session.session_summary
        ? `<p style="font-size:0.875rem;color:#b0b0b0;margin-bottom:0.75rem;line-height:1.5;">${session.session_summary}</p>`
        : '';

      detailsEl.innerHTML = `
        ${summaryBlock}
        <div class="mb-3">
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold">Phase:</span>
            <span>${session.phase_name || ''}</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold">Location:</span>
            <span class="capitalize">${session.location || ''}</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold">Duration:</span>
            <span>${session.estimated_duration || session.estimated_duration_minutes || ''} min</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="font-semibold">Intensity:</span>
            <span>${session.intended_intensity_rpe ? `RPE ${session.intended_intensity_rpe}/10` : 'As prescribed'}</span>
          </div>
        </div>

        ${session.exercise_names && session.exercise_names.length ? `
        <div style="background:rgba(255,255,255,0.05);padding:0.75rem;border-radius:8px;">
          <p style="font-size:0.8rem;color:#b0b0b0;margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.5px;">Today's Exercises</p>
          <ul style="list-style:none;padding:0;margin:0;">
            ${session.exercise_names.map(n => `<li style="font-size:0.875rem;color:#f5f5f5;padding:0.25rem 0;border-bottom:1px solid rgba(255,255,255,0.06);">${n}</li>`).join('')}
          </ul>
        </div>` : `
        <div style="background:rgba(255,255,255,0.05);padding:0.75rem;border-radius:8px;">
          <p style="font-size:0.8rem;color:#b0b0b0;margin-bottom:0.25rem;">Session Overview</p>
          <span style="font-size:0.875rem;">${session.exercise_count || 0} exercises planned</span>
        </div>`}
      `;
    }

    // Show start button
    const startBtn = document.getElementById('start-session-btn');
    if (startBtn) {
      startBtn.style.display = 'block';
    }
  }

  renderSessionComplete(summary) {
    // Update card header
    const card = document.getElementById('session-card');
    if (card) {
      const title = card.querySelector('.card-title');
      if (title) title.textContent = 'Session Complete!';
    }

    const focusEl = document.getElementById('session-focus');
    if (focusEl) focusEl.textContent = summary.focus || 'Training Session';

    const detailsEl = document.getElementById('session-details');
    if (detailsEl) {
      const exerciseRows = (summary.main_exercises || []).length
        ? `<div style="margin-top:0.75rem;background:rgba(255,255,255,0.05);padding:0.75rem;border-radius:8px;">
             <p style="font-size:0.75rem;color:#b0b0b0;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.5rem;">Completed</p>
             <ul style="list-style:none;padding:0;margin:0;">
               ${summary.main_exercises.map(e =>
                 `<li style="font-size:0.875rem;color:#f5f5f5;padding:0.2rem 0;">✓ ${e}</li>`
               ).join('')}
             </ul>
           </div>`
        : '';

      const rpeRow = summary.rpe
        ? `<div style="display:flex;justify-content:space-between;margin-top:0.5rem;">
             <span style="font-size:0.875rem;color:#b0b0b0;">Session RPE</span>
             <strong style="color:#f5f5f5;">${summary.rpe} / 10</strong>
           </div>`
        : '';

      // If there's a next session coming up, mention it
      const nextSession = this.dashboard && this.dashboard.next_session;
      const nextRow = nextSession
        ? `<div style="margin-top:0.75rem;padding:0.5rem 0.75rem;background:rgba(210,105,30,0.1);border-radius:8px;border-left:3px solid var(--bill-primary);">
             <p style="font-size:0.75rem;color:#b0b0b0;margin-bottom:0.15rem;">Next session</p>
             <p style="font-size:0.875rem;color:#f5f5f5;">${nextSession.focus || 'Training Session'} — ${nextSession.session_date || ''}</p>
           </div>`
        : '';

      detailsEl.innerHTML = `
        <div style="text-align:center;padding:1rem 0 0.5rem;">
          <div style="font-size:2.5rem;margin-bottom:0.4rem;">🎉</div>
          <p style="font-weight:700;color:#f5f5f5;font-size:1.1rem;">Great work!</p>
          <p style="font-size:0.875rem;color:#b0b0b0;margin-top:0.2rem;">Another session in the bank. Recovery starts now.</p>
        </div>
        ${rpeRow}
        ${exerciseRows}
        ${nextRow}
      `;
    }

    // Replace Start Session with View Progress
    const startBtn = document.getElementById('start-session-btn');
    if (startBtn) {
      startBtn.textContent = '📈 View Your Progress';
      startBtn.style.display = 'block';
    }
  }

  renderRestDay(nextSession) {
    const cardTitle = document.querySelector('#session-card .card-title');
    if (cardTitle) cardTitle.textContent = 'Rest Day';

    const focusEl = document.getElementById('session-focus');
    if (focusEl) focusEl.textContent = 'Recovery & preparation';

    // Format the upcoming session date nicely
    const nextDate = nextSession.session_date
      ? new Date(nextSession.session_date + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' })
      : '';

    const detailsEl = document.getElementById('session-details');
    if (detailsEl) {
      detailsEl.innerHTML = `
        <div style="text-align:center;padding:0.75rem 0 0.5rem;">
          <div style="font-size:2rem;margin-bottom:0.4rem;">🛌</div>
          <p style="font-weight:600;color:#f5f5f5;">Today is a rest day.</p>
          <p style="font-size:0.875rem;color:#b0b0b0;margin-top:0.25rem;line-height:1.5;">
            Recovery is where the gains happen. Rest up, stay hydrated, and come back ready.
          </p>
        </div>
        ${nextSession ? `
        <div style="margin-top:1rem;padding:0.75rem;background:rgba(210,105,30,0.1);border-radius:8px;border-left:3px solid var(--bill-primary);">
          <p style="font-size:0.75rem;color:#b0b0b0;margin-bottom:0.2rem;text-transform:uppercase;letter-spacing:0.5px;">Coming up</p>
          <p style="font-size:0.95rem;font-weight:600;color:#f5f5f5;">${nextSession.focus || 'Training Session'}</p>
          <p style="font-size:0.8rem;color:#b0b0b0;margin-top:0.15rem;">${nextDate}</p>
        </div>` : ''}
      `;
    }

    // Hide start button on rest days
    const startBtn = document.getElementById('start-session-btn');
    if (startBtn) startBtn.style.display = 'none';
  }

  renderNoSession() {
    const detailsEl = document.getElementById('session-details');
    if (detailsEl) {
      const restMsg = this.restSummary
        ? `<p class="text-sm text-gray-500 mt-2">${this.restSummary}</p>`
        : '';
      detailsEl.innerHTML = `
        <div class="text-center py-4">
          <p class="text-gray-600 mb-2">No session scheduled for today</p>
          <p class="text-sm text-gray-500">Enjoy your rest day, or chat with Bill if you want to adjust your plan</p>
          ${restMsg}
        </div>
      `;
    }

    // Hide start button
    const startBtn = document.getElementById('start-session-btn');
    if (startBtn) {
      startBtn.style.display = 'none';
    }
  }

  setupEventListeners() {
    // Start session button
    const startBtn = document.getElementById('start-session-btn');
    if (startBtn) {
      startBtn.addEventListener('click', () => this.onStartSession());
    }

    // Chat button
    const chatBtn = document.getElementById('chat-btn');
    if (chatBtn) {
      chatBtn.addEventListener('click', () => this.onOpenChat());
    }
  }

  onStartSession() {
    // If the user just completed a session, the button routes to progress
    if (this.completedSummary) {
      window.location.href = '/progress.html';
      return;
    }

    if (!this.dashboard || !this.dashboard.next_session) {
      app.showError('No session available to start');
      return;
    }

    // Save session to app state
    app.setActiveSession(this.dashboard.next_session);

    // Navigate to session preview
    window.location.href = '/session-preview.html';
  }

  onOpenChat() {
    window.location.href = '/chat.html';
  }
}

// Initialize dashboard when DOM is ready
const dashboard = new Dashboard();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => dashboard.init());
} else {
  dashboard.init();
}
