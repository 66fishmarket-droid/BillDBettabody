// Bill D'Bettabody - Dashboard Logic
// Today screen functionality

class Dashboard {
  constructor() {
    this.profile = null;
    this.todaySession = null;
    this.nutrition = null;
  }

  async init() {
    console.log('[Dashboard] Initializing...');

    try {
      app.showLoading('Loading your day...');

      // Load all dashboard data
      await Promise.all([
        this.loadProfile(),
        this.loadTodaySession(),
        this.loadNutrition()
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

  async loadProfile() {
    this.profile = await api.getProfile();
    console.log('[Dashboard] Profile loaded:', this.profile);
  }

  async loadTodaySession() {
    this.todaySession = await api.getTodaySession();
    console.log('[Dashboard] Today session loaded:', this.todaySession);
  }

  async loadNutrition() {
    this.nutrition = await api.getDailyNutrition();
    console.log('[Dashboard] Nutrition loaded:', this.nutrition);
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
    if (this.profile) {
      const nameEl = document.getElementById('client-name');
      if (nameEl) {
        nameEl.textContent = `${this.profile.first_name} ${this.profile.last_name}`;
      }

      const sessionsEl = document.getElementById('sessions-completed');
      if (sessionsEl) {
        sessionsEl.textContent = this.profile.sessions_completed || 0;
      }

      const weekEl = document.getElementById('current-week');
      if (weekEl) {
        weekEl.textContent = this.profile.current_phase || 'Starting soon';
      }
    }

    // Today's session
    if (this.todaySession && this.todaySession.session) {
      this.renderSession(this.todaySession);
    } else {
      this.renderNoSession();
    }

    // Nutrition
    if (this.nutrition) {
      const caloriesEl = document.getElementById('calories-target');
      if (caloriesEl) {
        caloriesEl.textContent = this.nutrition.calories || 0;
      }

      const proteinEl = document.getElementById('protein-target');
      if (proteinEl) {
        proteinEl.textContent = `${this.nutrition.protein || 0}g`;
      }
    }
  }

  renderSession(sessionData) {
    const session = sessionData.session;
    const stepCount = sessionData.stepCount;

    // Session focus
    const focusEl = document.getElementById('session-focus');
    if (focusEl) {
      focusEl.textContent = session.focus;
    }

    // Session details
    const detailsEl = document.getElementById('session-details');
    if (detailsEl) {
      detailsEl.innerHTML = `
        <div class="mb-3">
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold">Phase:</span>
            <span>${session.phase}</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold">Location:</span>
            <span class="capitalize">${session.location}</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold">Duration:</span>
            <span>${session.estimated_duration_minutes} min</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="font-semibold">Intensity:</span>
            <span>RPE ${session.intended_intensity_rpe}/10</span>
          </div>
        </div>

        <div class="bg-gray-50 p-3 rounded-lg">
          <p class="text-sm text-gray-600 mb-2">Session Overview:</p>
          <div class="flex justify-between text-sm">
            <span><span class="badge badge-warmup">Warm-up</span> ${stepCount.warmup} exercises</span>
            <span><span class="badge badge-main">Main</span> ${stepCount.main} exercises</span>
            <span><span class="badge badge-cooldown">Cool-down</span> ${stepCount.cooldown} exercises</span>
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
      detailsEl.innerHTML = `
        <div class="text-center py-4">
          <p class="text-gray-600 mb-2">No session scheduled for today</p>
          <p class="text-sm text-gray-500">Enjoy your rest day, or chat with Bill if you want to adjust your plan</p>
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
    if (!this.todaySession || !this.todaySession.session) {
      app.showError('No session available to start');
      return;
    }

    // Save session to app state
    app.setActiveSession(this.todaySession.session);

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
