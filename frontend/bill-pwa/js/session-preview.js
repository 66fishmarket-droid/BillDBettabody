// Bill D'Bettabody - Session Preview Logic
// Pre-workout overview screen

class SessionPreview {
  constructor() {
    this.session = null;
    this.steps = [];
    this.equipment = new Set();
  }

  async init() {
    console.log('[Session Preview] Initializing...');

    try {
      // Get active session from app state
      this.session = app.getActiveSession();

      if (!this.session) {
        console.error('[Session Preview] No active session found');
        app.showError('No session selected. Returning to dashboard.');
        setTimeout(() => window.location.href = '/dashboard.html', 2000);
        return;
      }

      app.showLoading('Loading session details...');

      // Load session steps
      await this.loadSessionSteps();

      // Render the preview
      this.render();

      // Setup event listeners
      this.setupEventListeners();

      app.hideLoading();
    } catch (error) {
      console.error('[Session Preview] Initialization failed:', error);
      app.hideLoading();
      app.showError('Failed to load session. Please try again.');
    }
  }

  async loadSessionSteps() {
    const data = await api.getSessionDetail(this.session.session_id, app.sessionId);
    this.steps = data.steps || [];
    console.log('[Session Preview] Steps loaded:', this.steps.length);

    // Extract equipment from Exercise Library join
    this.steps.forEach(step => {
      if (step.equipment) {
        step.equipment.split(',').forEach(e => {
          const trimmed = e.trim();
          if (trimmed) this.equipment.add(trimmed);
        });
      }
    });
  }

  render() {
    // Session header
    document.getElementById('session-name').textContent =
      this.session.focus || 'Training Session';

    document.getElementById('session-focus').textContent =
      this.session.session_summary || '';

    document.getElementById('session-phase').textContent =
      this.session.phase_name || '';

    document.getElementById('session-location').textContent =
      this.session.location || 'gym';

    document.getElementById('session-duration').textContent =
      `${this.session.estimated_duration || 45} min`;

    document.getElementById('session-intensity').textContent =
      `RPE ${this.session.intended_intensity_rpe || 7}/10`;

    // Render exercises by segment
    this.renderExerciseSegment('warmup', 'warmup-exercises', 'warmup-duration');
    this.renderExerciseSegment('main', 'main-exercises', 'main-duration');
    this.renderExerciseSegment('cooldown', 'cooldown-exercises', 'cooldown-duration');

    // Render equipment
    this.renderEquipment();

    // Only show Start Session for scheduled (upcoming) sessions
    const status = (this.session.status || '').toLowerCase();
    if (status !== 'scheduled' && status !== '') {
      document.getElementById('start-bar').style.display = 'none';
    }
  }

  renderExerciseSegment(segmentType, elementId, durationId) {
    // Map with original index so we can look up the step on click
    const exercises = this.steps
      .map((step, idx) => ({ step, idx }))
      .filter(({ step }) => (step.segment_type || '').toLowerCase() === segmentType);

    const listEl   = document.getElementById(elementId);
    const durationEl = document.getElementById(durationId);

    if (!exercises.length) {
      listEl.innerHTML = '<li style="font-size:0.875rem;color:#b0b0b0;padding:0.5rem 0;">No exercises</li>';
      return;
    }

    // Estimated duration
    let totalMinutes = 0;
    exercises.forEach(({ step }) => {
      if (step.duration_value) {
        totalMinutes += Number(step.duration_value);
      } else if (step.sets && step.rest_seconds) {
        totalMinutes += ((30 + Number(step.rest_seconds)) * Number(step.sets)) / 60;
      }
    });

    if (durationEl && totalMinutes > 0) {
      durationEl.textContent = `~${Math.round(totalMinutes)} min`;
    }

    // Render exercise list — all exercises are always clickable
    listEl.innerHTML = exercises.map(({ step, idx }) => {
      const detail = this.getExerciseDetail(step);
      return `
        <li class="exercise-list-item ${segmentType}"
            data-step-idx="${idx}"
            style="cursor:pointer;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
            <div style="flex:1;min-width:0;">
              <div style="font-weight:600;color:#f5f5f5;margin-bottom:0.15rem;">${this.esc(step.exercise_name)}</div>
              <div style="font-size:0.875rem;color:#b0b0b0;">${detail}</div>
            </div>
            <span style="color:var(--bill-primary);font-size:0.9rem;flex-shrink:0;margin-top:0.1rem;">›</span>
          </div>
        </li>
      `;
    }).join('');

    // Delegated click listener — all items open the modal
    listEl.addEventListener('click', (e) => {
      const li = e.target.closest('[data-step-idx]');
      if (!li) return;
      const idx = parseInt(li.dataset.stepIdx, 10);
      if (!isNaN(idx)) this.openExerciseModal(this.steps[idx]);
    });
  }

  getExerciseDetail(step) {
    const parts = [];

    if (step.sets && step.reps) {
      parts.push(`${step.sets} × ${step.reps}`);
    } else if (step.duration_value && step.duration_type === 'time') {
      parts.push(`${step.duration_value} min`);
    }

    if (step.load_kg) {
      parts.push(`${step.load_kg}kg`);
    }

    if (step.target_value && !String(step.target_value).includes('undefined')) {
      parts.push(step.target_value);
    }

    return parts.length > 0 ? parts.join(' • ') : 'As prescribed';
  }

  renderEquipment() {
    const equipmentEl = document.getElementById('equipment-list');

    if (this.equipment.size === 0) {
      document.getElementById('equipment-card').style.display = 'none';
      return;
    }

    equipmentEl.innerHTML = Array.from(this.equipment)
      .map(item => `
        <span class="badge bg-gray-200 text-gray-700 px-3 py-1 rounded-full text-sm">
          ${item}
        </span>
      `)
      .join('');
  }

  // ─── Exercise detail modal ───────────────────────────────────────────────

  openExerciseModal(step) {
    document.getElementById('ex-modal-title').textContent = step.exercise_name || 'Exercise';

    const sections = [];

    // YouTube embed or plain link
    const embedUrl = this._youtubeEmbedUrl(step.video_url);
    if (embedUrl) {
      sections.push(`
        <div class="ex-modal-section">
          <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;background:#000;">
            <iframe src="${embedUrl}"
              style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen></iframe>
          </div>
        </div>`);
    } else if (step.video_url) {
      sections.push(`<div class="ex-modal-section"><h4>Video</h4><p><a href="${this.esc(step.video_url)}" target="_blank" rel="noopener" style="color:var(--bill-primary-light);">▶ Watch Video</a></p></div>`);
    }

    // Prescription — always show
    const prescParts = [];
    if (step.sets && step.reps) prescParts.push(`${step.sets} sets × ${step.reps} reps`);
    if (step.load_kg)           prescParts.push(`Load: ${step.load_kg} kg`);
    if (step.tempo_pattern)     prescParts.push(`Tempo: ${step.tempo_pattern}`);
    if (step.rest_seconds)      prescParts.push(`Rest: ${step.rest_seconds}s`);
    if (step.notes_coach)       prescParts.push(`Coach: ${step.notes_coach}`);
    if (prescParts.length) {
      sections.push(`<div class="ex-modal-section"><h4>Prescription</h4><p>${prescParts.map(p => this.esc(p)).join('<br>')}</p></div>`);
    }

    if (step.exercise_description_long) {
      sections.push(`<div class="ex-modal-section"><h4>Description</h4><p>${this.esc(step.exercise_description_long)}</p></div>`);
    }
    if (step.coaching_cues_short) {
      sections.push(`<div class="ex-modal-section"><h4>Coaching Cues</h4><p>${this.esc(step.coaching_cues_short)}</p></div>`);
    }
    if (step.safety_notes) {
      sections.push(`<div class="ex-modal-section"><h4>Safety Notes</h4><p>${this.esc(step.safety_notes)}</p></div>`);
    }
    if (step.common_mistakes) {
      sections.push(`<div class="ex-modal-section"><h4>Common Mistakes</h4><p>${this.esc(step.common_mistakes)}</p></div>`);
    }
    if (step.regression) {
      sections.push(`<div class="ex-modal-section"><h4>Easier Options</h4><p>${this.esc(step.regression)}</p></div>`);
    }
    if (step.progression) {
      sections.push(`<div class="ex-modal-section"><h4>Harder Options</h4><p>${this.esc(step.progression)}</p></div>`);
    }

    document.getElementById('ex-modal-body').innerHTML =
      sections.join('') || '<p style="color:#b0b0b0;">No additional details available.</p>';

    document.getElementById('ex-modal').hidden = false;
  }

  closeExerciseModal() {
    // Clear body so embedded videos stop playing
    document.getElementById('ex-modal-body').innerHTML = '';
    document.getElementById('ex-modal').hidden = true;
  }

  _youtubeEmbedUrl(url) {
    if (!url) return null;
    const match = String(url).match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    return match ? `https://www.youtube.com/embed/${match[1]}` : null;
  }

  esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ─── Event listeners ─────────────────────────────────────────────────────

  setupEventListeners() {
    // Back button
    document.getElementById('back-btn').addEventListener('click', () => {
      window.location.href = '/dashboard.html';
    });

    // Ask Bill button
    document.getElementById('ask-bill-btn').addEventListener('click', () => {
      localStorage.setItem('chat_context', JSON.stringify({
        type: 'session_preview',
        session_id: this.session.session_id,
        session_name: this.session.focus
      }));
      window.location.href = '/chat.html';
    });

    // Start session button
    document.getElementById('start-session-btn').addEventListener('click', () => {
      this.onStartSession();
    });

    // Modal close
    document.getElementById('ex-modal-close').addEventListener('click', () => this.closeExerciseModal());
    document.getElementById('ex-modal').addEventListener('click', e => {
      if (e.target === document.getElementById('ex-modal')) this.closeExerciseModal();
    });
  }

  onStartSession() {
    console.log('[Session Preview] Starting session...');
    localStorage.setItem('active_session_steps', JSON.stringify(this.steps));
    window.location.href = '/session-active.html';
  }
}

// Initialize session preview when DOM is ready
const sessionPreview = new SessionPreview();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => sessionPreview.init());
} else {
  sessionPreview.init();
}
