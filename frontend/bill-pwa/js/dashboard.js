// Bill D'Bettabody - Dashboard Logic
// Today screen functionality

class Dashboard {
  constructor() {
    this.dashboard = null;
    this.restSummary = null;
    this.profile = null;
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
      const completed = this.profile && this.profile.completed_sessions;
      sessionsEl.textContent = completed || 0;
    }

    const weekEl = document.getElementById('current-week');
    if (weekEl) {
      const block = this.dashboard ? this.dashboard.block_summary : null;
      weekEl.textContent = block && block.week_number
        ? `Week ${block.week_number}`
        : 'Starting soon';
    }

    // Today's session
    if (this.dashboard && this.dashboard.next_session) {
      this.renderSession(this.dashboard);
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
      detailsEl.innerHTML = `
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

        <div class="bg-gray-50 p-3 rounded-lg">
          <p class="text-sm text-gray-600 mb-2">Session Overview:</p>
          <div class="flex justify-between text-sm">
            <span>${session.exercise_count || 0} total exercises</span>
          </div>
        </div>
      `;
    }

    // Show start button
    const startBtn = document.getElementById('start-session-btn');
    if (startBtn) {
      startBtn.style.display = 'block';
    }
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
