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
    const data = await api.getSessionSteps(this.session.session_id);
    this.steps = data.steps || [];
    console.log('[Session Preview] Steps loaded:', this.steps.length);

    // Extract equipment
    this.steps.forEach(step => {
      if (step.exercise_name) {
        // Simple equipment detection from exercise names
        // Later we can enhance this with actual equipment data from Exercise Library
        if (step.exercise_name.includes('Barbell')) this.equipment.add('Barbell');
        if (step.exercise_name.includes('Dumbbell')) this.equipment.add('Dumbbells');
        if (step.exercise_name.includes('Machine') || step.exercise_name.includes('Leg Curl')) this.equipment.add('Machines');
        if (step.exercise_name.includes('Band')) this.equipment.add('Resistance Bands');
        if (step.exercise_name.includes('Bike') || step.exercise_name.includes('Assault Bike')) this.equipment.add('Cardio Equipment');
        if (step.exercise_name.includes('Box') || step.exercise_name.includes('Bulgarian')) this.equipment.add('Bench/Box');
      }
    });
  }

  render() {
    // Session header
    document.getElementById('session-name').textContent = 
      this.session.phase || 'Training Session';
    
    document.getElementById('session-focus').textContent = 
      this.session.focus || '';
    
    document.getElementById('session-phase').textContent = 
      this.session.phase || '';
    
    document.getElementById('session-location').textContent = 
      this.session.location || 'gym';
    
    document.getElementById('session-duration').textContent = 
      `${this.session.estimated_duration_minutes || 45} min`;
    
    document.getElementById('session-intensity').textContent = 
      `RPE ${this.session.intended_intensity_rpe || 7}/10`;

    // Render exercises by segment
    this.renderExerciseSegment('warmup', 'warmup-exercises', 'warmup-duration');
    this.renderExerciseSegment('main', 'main-exercises', 'main-duration');
    this.renderExerciseSegment('cooldown', 'cooldown-exercises', 'cooldown-duration');

    // Render equipment
    this.renderEquipment();
  }

  renderExerciseSegment(segmentType, elementId, durationId) {
    const exercises = this.steps.filter(step => 
      step.segment_type === segmentType
    );

    const listEl = document.getElementById(elementId);
    const durationEl = document.getElementById(durationId);

    if (!exercises.length) {
      listEl.innerHTML = '<li class="text-gray-500 text-sm">No exercises</li>';
      return;
    }

    // Calculate estimated duration for this segment
    let totalMinutes = 0;
    exercises.forEach(step => {
      if (step.duration_value) {
        totalMinutes += step.duration_value;
      } else if (step.sets && step.rest_seconds) {
        // Estimate: 30 sec per set + rest time
        totalMinutes += ((30 + step.rest_seconds) * step.sets) / 60;
      }
    });

    if (durationEl && totalMinutes > 0) {
      durationEl.textContent = `~${Math.round(totalMinutes)} min`;
    }

    // Render exercise list
    listEl.innerHTML = exercises.map(step => {
      const detail = this.getExerciseDetail(step);
      return `
        <li class="exercise-list-item ${segmentType}">
          <div class="font-semibold text-gray-900">${step.exercise_name}</div>
          <div class="text-sm text-gray-600">${detail}</div>
        </li>
      `;
    }).join('');
  }

  getExerciseDetail(step) {
    // Format exercise prescription concisely
    const parts = [];

    if (step.sets && step.reps) {
      parts.push(`${step.sets} × ${step.reps}`);
    } else if (step.duration_value && step.duration_type === 'time') {
      parts.push(`${step.duration_value} min`);
    }

    if (step.load_kg) {
      parts.push(`${step.load_kg}kg`);
    }

    if (step.target_value && !step.target_value.includes('undefined')) {
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

  setupEventListeners() {
    // Back button
    document.getElementById('back-btn').addEventListener('click', () => {
      window.location.href = '/dashboard.html';
    });

    // Ask Bill button
    document.getElementById('ask-bill-btn').addEventListener('click', () => {
      // Store session context for chat
      localStorage.setItem('chat_context', JSON.stringify({
        type: 'session_preview',
        session_id: this.session.session_id,
        session_name: this.session.phase
      }));
      window.location.href = '/chat.html';
    });

    // Start session button
    document.getElementById('start-session-btn').addEventListener('click', () => {
      this.onStartSession();
    });
  }

  onStartSession() {
    console.log('[Session Preview] Starting session...');
    
    // Store full session data for active session
    localStorage.setItem('active_session_steps', JSON.stringify(this.steps));
    
    // Navigate to active session screen
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
