// Bill D'Bettabody - Active Session Logging

class SessionActive {
  constructor() {
    this.session = null;
    this.steps = [];
  }

  init() {
    this.session = app.getActiveSession();
    const storedSteps = localStorage.getItem('active_session_steps');
    this.steps = storedSteps ? JSON.parse(storedSteps) : [];

    if (!this.session || !this.steps.length) {
      app.showError('No active session data. Returning to dashboard.');
      setTimeout(() => window.location.href = '/dashboard.html', 1500);
      return;
    }

    this.renderHeader();
    this.renderSteps();
    this.bindEvents();
  }

  renderHeader() {
    const titleEl = document.getElementById('session-title');
    const subtitleEl = document.getElementById('session-subtitle');

    if (titleEl) {
      titleEl.textContent = this.session.focus || 'Active Session';
    }
    if (subtitleEl) {
      subtitleEl.textContent = this.session.session_date
        ? app.formatDate(this.session.session_date)
        : '';
    }
  }

  renderSteps() {
    const container = document.getElementById('steps-container');
    if (!container) return;

    container.innerHTML = this.steps.map((step, idx) => {
      const notes = step.notes_athlete || '';
      const isMain = (step.segment_type || '').toLowerCase() === 'main';
      const defaultMetric = this.getDefaultMetric(step);

      const setRows = isMain ? Array.from({ length: 5 }).map((_, setIdx) => {
        const setNum = setIdx + 1;
        return `
          <div class="grid grid-cols-3 gap-2 mb-2">
            <div>
              <label class="block text-xs text-muted mb-1">Set ${setNum} Reps</label>
              <input data-step="${idx}" data-field="actual_set${setNum}_reps" type="number" min="0"
                     class="w-full px-2 py-1 bg-gray-800 border border-gray-600 rounded text-white">
            </div>
            <div>
              <label class="block text-xs text-muted mb-1">Set ${setNum} Value</label>
              <input data-step="${idx}" data-field="actual_set${setNum}_value" type="number" min="0"
                     class="w-full px-2 py-1 bg-gray-800 border border-gray-600 rounded text-white">
            </div>
            <div>
              <label class="block text-xs text-muted mb-1">Set ${setNum} Metric</label>
              <select data-step="${idx}" data-field="actual_set${setNum}_metric"
                      class="w-full px-2 py-1 bg-gray-800 border border-gray-600 rounded text-white">
                <option value="">Select</option>
                <option value="kg" ${defaultMetric === 'kg' ? 'selected' : ''}>kg</option>
                <option value="lb" ${defaultMetric === 'lb' ? 'selected' : ''}>lb</option>
                <option value="reps" ${defaultMetric === 'reps' ? 'selected' : ''}>reps</option>
                <option value="sec" ${defaultMetric === 'sec' ? 'selected' : ''}>sec</option>
                <option value="min" ${defaultMetric === 'min' ? 'selected' : ''}>min</option>
                <option value="m" ${defaultMetric === 'm' ? 'selected' : ''}>m</option>
                <option value="km" ${defaultMetric === 'km' ? 'selected' : ''}>km</option>
                <option value="w" ${defaultMetric === 'w' ? 'selected' : ''}>w</option>
                <option value="cal" ${defaultMetric === 'cal' ? 'selected' : ''}>cal</option>
              </select>
            </div>
          </div>
        `;
      }).join('') : '';

      const mainLabel = isMain ? '' : '<div class="text-xs text-muted mb-2">Non‑main segment (optional notes only)</div>';

      return `
        <div class="card mb-3">
          <div class="mb-2">
            <div class="font-semibold">${step.exercise_name || 'Exercise'}</div>
            <div class="text-sm text-muted">${step.segment_type || ''}</div>
          </div>
          ${mainLabel}
          ${setRows}
          <div>
            <label class="block text-xs text-muted mb-1">Notes</label>
            <textarea data-step="${idx}" data-field="notes_athlete" rows="2"
                      class="w-full px-2 py-1 bg-gray-800 border border-gray-600 rounded text-white">${notes}</textarea>
          </div>
        </div>
      `;
    }).join('');
  }

  getDefaultMetric(step) {
    const metricKey = (step.metric_key || '').toLowerCase();
    const metricContext = (step.metric_context_key || '').toLowerCase();
    const name = (step.exercise_name || '').toLowerCase();

    if (metricKey.includes('kg') || metricKey.includes('load') || metricContext.includes('load')) {
      return 'kg';
    }
    if (metricKey.includes('lb')) {
      return 'lb';
    }
    if (metricKey.includes('sec') || metricKey.includes('time') || metricContext.includes('time')) {
      return 'sec';
    }
    if (metricKey.includes('min')) {
      return 'min';
    }
    if (metricKey.includes('m') || metricKey.includes('distance') || metricContext.includes('distance')) {
      return 'm';
    }
    if (metricKey.includes('km')) {
      return 'km';
    }
    if (metricKey.includes('w') || metricKey.includes('power') || metricContext.includes('power')) {
      return 'w';
    }
    if (metricKey.includes('cal')) {
      return 'cal';
    }

    // Heuristic by name
    if (name.includes('run') || name.includes('row') || name.includes('bike') || name.includes('swim')) {
      return 'm';
    }

    return 'kg';
  }

  bindEvents() {
    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', () => window.location.href = '/session-preview.html');
    }

    const askBtn = document.getElementById('ask-bill-btn');
    if (askBtn) {
      askBtn.addEventListener('click', () => {
        localStorage.setItem('chat_context', JSON.stringify({
          type: 'session_active',
          session_id: this.session.session_id,
          session_name: this.session.focus
        }));
        window.location.href = '/chat.html';
      });
    }

    const completeBtn = document.getElementById('complete-session-btn');
    if (completeBtn) {
      completeBtn.addEventListener('click', () => this.submitSession());
    }
  }

  collectStepUpdates() {
    const updates = this.steps.map((step) => ({
      step_id: step.step_id
    }));

    const inputs = document.querySelectorAll('[data-step][data-field]');
    inputs.forEach((input) => {
      const idx = Number(input.getAttribute('data-step'));
      const field = input.getAttribute('data-field');
      if (!updates[idx]) return;

      if (input.tagName.toLowerCase() === 'textarea') {
        const text = input.value.trim();
        if (text) updates[idx][field] = text;
        return;
      }

      const val = input.value;
      if (val === '') return;

      if (input.tagName.toLowerCase() === 'select') {
        updates[idx][field] = val;
      } else {
        updates[idx][field] = Number(val);
      }
    });

    // Remove updates that only contain step_id
    return updates.filter((u) => Object.keys(u).length > 1);
  }

  async submitSession() {
    try {
      app.showLoading('Submitting session...');

      const steps = this.collectStepUpdates();
      const rpe = document.getElementById('session-rpe').value;
      const notes = document.getElementById('session-notes').value.trim();

      const payload = {
        bill_session_id: app.sessionId,
        session_updates: {
          session_status: 'completed',
          notes: notes || '',
          session_summary: rpe ? `Session RPE: ${rpe}/10` : ''
        },
        steps_upsert: steps
      };

      await api.completeSession(this.session.session_id, payload);

      localStorage.removeItem('active_session_steps');
      app.clearActiveSession();

      app.hideLoading();
      window.location.href = '/dashboard.html';
    } catch (error) {
      console.error('[Session Active] Submit failed:', error);
      app.hideLoading();
      app.showError('Failed to submit session. Please try again.');
    }
  }
}

const sessionActive = new SessionActive();
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => sessionActive.init());
} else {
  sessionActive.init();
}
