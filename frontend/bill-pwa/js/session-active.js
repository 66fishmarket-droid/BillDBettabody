// Bill D'Bettabody - Active Session Logging

class SessionActive {
  constructor() {
    this.session = null;
    this.steps = [];
    this.stepSetCounts = [];
    this.restTimers = {};     // stepIdx → intervalId
    this.restRemaining = {};  // stepIdx → seconds remaining
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

    // Initial row counts per step
    this.stepSetCounts = this.steps.map(step => {
      if (!this.isWeightedStep(step)) return 0;
      if (this.isIntervalStep(step)) return 1; // intervals log as one set (reps = rounds completed)
      return Math.max(parseInt(step.sets, 10) || 1, 1);
    });

    this.renderHeader();
    this.renderSteps();
    this.bindEvents();
  }

  // ─── Pattern set builder ──────────────────────────────────────────────────

  // Computes per-set {load, reps, rpe} from pattern fields.
  // Returns an array with length == step.sets, ready for renderSetRow.
  buildPatternSets(step) {
    const pt        = (step.pattern_type || '').toUpperCase();
    const loadStart = parseFloat(step.load_start_kg)    || 0;
    const loadInc   = parseFloat(step.load_increment_kg) || 0;
    const loadPeak  = parseFloat(step.load_peak_kg)     || 0;
    const baseLoad  = parseFloat(step.load_kg)          || 0;
    const n         = Math.max(parseInt(step.sets, 10) || 1, 1);
    const baseReps  = step.reps  ? String(step.reps)  : '';
    const baseRpe   = step.target_value ? String(step.target_value) : '';

    const repsArr = step.reps_pattern ? step.reps_pattern.split(',').map(s => s.trim()) : [];
    const rpeArr  = step.rpe_pattern  ? step.rpe_pattern.split(',').map(s => this._normalizeRpe(s)) : [];
    const getReps = i => repsArr[i] || baseReps;
    const getRpe  = i => rpeArr[i]  || this._normalizeRpe(baseRpe);

    const sets = [];

    if (!pt || pt === 'STRENGTH_FLAT') {
      const load = loadStart || baseLoad;
      for (let i = 0; i < n; i++)
        sets.push({ load, reps: getReps(i), rpe: getRpe(i) });

    } else if (pt === 'STRENGTH_RAMP_TO_TARGET' || pt === 'STRENGTH_WARMUP_PLUS_FLAT_WORK') {
      let load = loadStart || baseLoad;
      for (let i = 0; i < n; i++) {
        sets.push({ load: loadPeak ? Math.min(load, loadPeak) : load, reps: getReps(i), rpe: getRpe(i) });
        if (loadInc && (!loadPeak || load < loadPeak)) load += loadInc;
      }

    } else if (pt === 'STRENGTH_TOP_SET_BACKOFF') {
      let load = loadStart || baseLoad;
      for (let i = 0; i < n; i++) {
        sets.push({ load, reps: getReps(i), rpe: getRpe(i) });
        if (loadPeak && load < loadPeak) load = Math.min(load + loadInc, loadPeak);
      }

    } else if (pt === 'STRENGTH_REVERSE_PYRAMID') {
      let load = loadStart || loadPeak || baseLoad;
      for (let i = 0; i < n; i++) {
        sets.push({ load: Math.max(0, load), reps: getReps(i), rpe: getRpe(i) });
        load -= Math.abs(loadInc);
      }

    } else if (pt === 'STRENGTH_LINEAR_PYRAMID') {
      const mid = Math.ceil(n / 2);
      let load = loadStart || baseLoad;
      for (let i = 0; i < n; i++) {
        sets.push({ load: Math.max(0, load), reps: getReps(i), rpe: getRpe(i) });
        if (i < mid - 1) load += Math.abs(loadInc);
        else              load -= Math.abs(loadInc);
      }

    } else if (pt === 'STRENGTH_DROP_SET') {
      let load = loadStart || loadPeak || baseLoad;
      for (let i = 0; i < n; i++) {
        sets.push({ load: Math.max(0, load), reps: getReps(i), rpe: getRpe(i) });
        load -= Math.abs(loadInc);
      }

    } else {
      // Any other pattern — flat with base values
      const load = loadStart || baseLoad;
      for (let i = 0; i < n; i++)
        sets.push({ load, reps: getReps(i), rpe: getRpe(i) });
    }

    return sets;
  }

  // ─── Step classification ──────────────────────────────────────────────────

  // Main-segment exercises that get per-set/per-round logging
  isWeightedStep(step) {
    if ((step.segment_type || '').toLowerCase() !== 'main') return false;
    return parseInt(step.sets, 10) > 0 || parseInt(step.interval_count, 10) > 0;
  }

  isIntervalStep(step) {
    return parseInt(step.interval_count, 10) > 0 || parseInt(step.interval_work_sec, 10) > 0;
  }

  // Returns input mode for a main-segment step.
  // feeder_set always reps_load_rpe; intervals handled separately in renderWeightedStep.
  getInputMode(step) {
    if (step.step_type === 'feeder_set') return 'reps_load_rpe';
    const hasLoad = parseFloat(step.load_kg) > 0 || parseFloat(step.load_start_kg) > 0;
    if (step.duration_type === 'time' || step.step_type === 'hold') return 'time_rpe';
    if (step.duration_type === 'distance') return 'distance_rpe';
    if (!hasLoad && parseInt(step.reps, 10) > 0) return 'reps_rpe';
    return 'reps_load_rpe';
  }

  // ─── Header ───────────────────────────────────────────────────────────────

  renderHeader() {
    const titleEl    = document.getElementById('session-title');
    const subtitleEl = document.getElementById('session-subtitle');
    if (titleEl)    titleEl.textContent    = this.session.focus || 'Active Session';
    if (subtitleEl) subtitleEl.textContent = this.session.session_date
      ? app.formatDate(this.session.session_date) : '';
  }

  // ─── Steps ────────────────────────────────────────────────────────────────

  renderSteps() {
    const container = document.getElementById('steps-container');
    if (!container) return;
    container.innerHTML = this.steps.map((step, idx) =>
      this.isWeightedStep(step)
        ? this.renderWeightedStep(step, idx)
        : this.renderSimpleStep(step, idx)
    ).join('');
  }

  renderWeightedStep(step, idx) {
    const isInterval     = this.isIntervalStep(step);
    const inputMode      = isInterval ? 'reps_load_rpe' : this.getInputMode(step);
    const setCount       = this.stepSetCounts[idx];
    const metric         = this.getDefaultMetric(step);
    const valueLabel     = this.getValueLabel(metric);
    const repsHeader     = isInterval ? 'Round' : 'Reps';
    const recommendedLoad = parseFloat(step.recommended_load_kg) || null;
    const prescription   = isInterval
      ? this.buildIntervalPrescription(step)
      : this.buildWeightedPrescription(step);

    // Column headers depend on input mode
    let headerHtml;
    if (inputMode === 'time_rpe') {
      headerHtml = `<span></span><span>Time</span><span>RPE</span>`;
    } else if (inputMode === 'distance_rpe') {
      headerHtml = `<span></span><span>Distance</span><span>RPE</span>`;
    } else if (inputMode === 'reps_rpe') {
      headerHtml = `<span></span><span>${repsHeader}</span><span>RPE</span>`;
    } else {
      headerHtml = `<span></span><span>${repsHeader}</span><span class="value-label-header">${valueLabel}</span><span>RPE</span>`;
    }

    const headerClass = (inputMode === 'reps_load_rpe') ? 'sets-header' : 'sets-header grid-3col';

    return `
      <div class="card mb-3 exercise-step-card" data-step-idx="${idx}">
        <div class="step-segment-tag segment-main">Main</div>
        <div class="step-exercise-name">${this.esc(step.exercise_name) || 'Exercise'}</div>
        ${step.exercise_description_short ? `<div class="step-exercise-desc">${this.esc(step.exercise_description_short)}</div>` : ''}
        ${prescription}
        <div class="step-divider"></div>

        <div class="${headerClass}">
          ${headerHtml}
        </div>
        <div class="sets-hint">Numbers pre-filled from your plan — tap ○ to confirm a set, or adjust first</div>

        <div class="sets-rows" id="sets-rows-${idx}">
          ${this.buildPatternSets(step).map((ps, i) => this.renderSetRow(idx, i + 1, inputMode, recommendedLoad, ps)).join('')}
        </div>

        ${this.renderRestTimer(step, idx)}

        <div class="step-actions-row">
          <div>
            <button class="add-set-btn" data-step="${idx}" ${setCount >= 10 ? 'disabled' : ''}>
              + Add Set
            </button>
            <div class="add-set-hint">add extra sets</div>
          </div>
          ${inputMode === 'reps_load_rpe' ? `
          <div class="metric-selector">
            <label>Unit:</label>
            <select class="exercise-metric-select" data-step="${idx}">
              ${this.metricOptions(metric)}
            </select>
          </div>` : ''}
        </div>

        ${this.renderInfoButtons(step, idx)}

        <textarea data-step="${idx}" data-field="notes_athlete" rows="2"
                  class="step-notes-input"
                  placeholder="Notes (optional)...">${this.esc(step.notes_athlete) || ''}</textarea>
      </div>
    `;
  }

  // prescribed = {load, reps, rpe} — per-set values from buildPatternSets().
  // load is pre-filled as a value; reps/rpe shown as placeholders.
  // The done-toggle button (set number) must be tapped to confirm the set —
  // any input change auto-confirms it. Only confirmed sets are saved.
  renderSetRow(stepIdx, setNum, mode, recommendedLoad, prescribed = {}) {
    const m    = mode || 'reps_load_rpe';
    const pRpe = this._normalizeRpe(prescribed.rpe);
    const doneBtn = `<button class="set-done-btn" data-step="${stepIdx}" data-set="${setNum}" data-done="false" aria-label="Confirm set ${setNum}">${setNum}</button>`;

    const rowAttrs = (extraClass = '') => [
      `class="set-row${extraClass ? ' ' + extraClass : ''}"`,
      `data-set-num="${setNum}"`,
      `data-prescribed-load="${prescribed.load || ''}"`,
      `data-prescribed-reps="${prescribed.reps || ''}"`,
      `data-prescribed-rpe="${pRpe}"`,
    ].join(' ');

    if (m === 'time_rpe') {
      return `
        <div ${rowAttrs('grid-3col')}>
          ${doneBtn}
          <input class="set-input" type="text" inputmode="decimal"
                 data-step="${stepIdx}" data-set="${setNum}" data-field-type="value" placeholder="mm:ss">
          <input class="set-input" type="number" min="1" max="10" inputmode="numeric" pattern="[0-9]*"
                 data-step="${stepIdx}" data-set="${setNum}" data-field-type="rpe"
                 placeholder="${pRpe || '—'}">
        </div>`;
    }

    if (m === 'distance_rpe') {
      return `
        <div ${rowAttrs('grid-3col')}>
          ${doneBtn}
          <input class="set-input" type="number" min="0" step="1" inputmode="decimal" pattern="[0-9.]*"
                 data-step="${stepIdx}" data-set="${setNum}" data-field-type="value" placeholder="—">
          <input class="set-input" type="number" min="1" max="10" inputmode="numeric" pattern="[0-9]*"
                 data-step="${stepIdx}" data-set="${setNum}" data-field-type="rpe"
                 placeholder="${pRpe || '—'}">
        </div>`;
    }

    if (m === 'reps_rpe') {
      return `
        <div ${rowAttrs('grid-3col')}>
          ${doneBtn}
          <input class="set-input" type="number" min="0" inputmode="numeric" pattern="[0-9]*"
                 data-step="${stepIdx}" data-set="${setNum}" data-field-type="reps"
                 placeholder="${prescribed.reps || '—'}">
          <input class="set-input" type="number" min="1" max="10" inputmode="numeric" pattern="[0-9]*"
                 data-step="${stepIdx}" data-set="${setNum}" data-field-type="rpe"
                 placeholder="${pRpe || '—'}">
        </div>`;
    }

    // reps_load_rpe — prescribed load pre-filled as value; reps/rpe as placeholders
    const loadVal  = prescribed.load || recommendedLoad || null;
    const loadAttr = loadVal ? ` value="${loadVal}"` : '';
    return `
      <div ${rowAttrs()}>
        ${doneBtn}
        <input class="set-input" type="number" min="0" inputmode="numeric" pattern="[0-9]*"
               data-step="${stepIdx}" data-set="${setNum}" data-field-type="reps"
               placeholder="${prescribed.reps || '—'}">
        <input class="set-input" type="number" min="0" step="0.5" inputmode="decimal" pattern="[0-9.]*"
               data-step="${stepIdx}" data-set="${setNum}" data-field-type="value"
               placeholder="—"${loadAttr}>
        <input class="set-input" type="number" min="1" max="10" inputmode="numeric" pattern="[0-9]*"
               data-step="${stepIdx}" data-set="${setNum}" data-field-type="rpe"
               placeholder="${pRpe || '—'}">
      </div>`;
  }

  renderSimpleStep(step, idx) {
    const segment  = (step.segment_type || '').toLowerCase();
    const tagLabel = segment === 'warmup' ? 'Warm-Up' : segment === 'cooldown' ? 'Cool-Down' : 'Exercise';

    return `
      <div class="card mb-3 exercise-step-card" data-step-idx="${idx}">
        <div class="step-segment-tag segment-${segment}">${tagLabel}</div>
        <div class="step-exercise-name">${this.esc(step.exercise_name) || 'Exercise'}</div>
        ${step.exercise_description_short ? `<div class="step-exercise-desc">${this.esc(step.exercise_description_short)}</div>` : ''}
        ${this.buildSimplePrescription(step)}
        <div class="step-divider"></div>
        ${this.renderInfoButtons(step, idx)}
        <textarea data-step="${idx}" data-field="notes_athlete" rows="2"
                  class="step-notes-input"
                  placeholder="Notes (optional)...">${this.esc(step.notes_athlete) || ''}</textarea>
      </div>
    `;
  }

  // Toggle the inline details panel for a step. Closes all others first.
  toggleDetailsPanel(stepIdx, btn) {
    const panel = document.getElementById(`details-panel-${stepIdx}`);
    if (!panel) return;
    const isOpen = !panel.hidden;

    // Close all open panels
    document.querySelectorAll('.step-details-panel').forEach(p => {
      p.hidden = true;
    });
    document.querySelectorAll('.details-toggle-btn').forEach(b => {
      b.textContent = 'Details ▼';
    });

    // Toggle this one
    if (!isOpen) {
      panel.hidden = false;
      if (btn) btn.textContent = 'Details ▲';
    }
  }

  // Build the inline details panel content for a step.
  renderDetailsPanel(step, idx) {
    const sections = [];

    // Pattern prescription info
    if (step.pattern_type) {
      const rows = [];
      const p = [`<strong>Pattern:</strong> ${this.esc(step.pattern_type)}`];
      if (parseFloat(step.load_start_kg) > 0)     p.push(`Start: ${this.formatLoad(step.load_start_kg, step)}`);
      if (parseFloat(step.load_increment_kg) > 0)  p.push(`+${step.load_increment_kg}kg/set`);
      if (parseFloat(step.load_peak_kg) > 0)       p.push(`Peak: ${this.formatLoad(step.load_peak_kg, step)}`);
      rows.push(`<p>${p.join('  •  ')}</p>`);
      if (step.reps_pattern)          rows.push(`<p>Reps: ${this.formatPattern(step.reps_pattern)}</p>`);
      if (step.rpe_pattern)           rows.push(`<p>RPE targets: ${this.formatPattern(step.rpe_pattern)}</p>`);
      if (step.tempo_per_set_pattern) rows.push(`<p>Tempo per set: ${this.formatPattern(step.tempo_per_set_pattern)}</p>`);
      if (step.pattern_notes)         rows.push(`<p><em>${this.esc(step.pattern_notes)}</em></p>`);
      sections.push(`<div class="details-section">
        <div class="details-label">Loading Pattern</div>
        ${rows.join('')}
      </div>`);
    }

    if (step.notes_coach) {
      sections.push(`<div class="details-section">
        <div class="details-label">Coach Notes</div>
        <p>${this.esc(step.notes_coach)}</p>
      </div>`);
    }
    if (step.coaching_cues_short) {
      sections.push(`<div class="details-section">
        <div class="details-label">Key Cues</div>
        <p>${this.esc(step.coaching_cues_short)}</p>
      </div>`);
    }
    if (step.exercise_description_long) {
      sections.push(`<div class="details-section">
        <div class="details-label">How to do it</div>
        <p>${this.esc(step.exercise_description_long)}</p>
      </div>`);
    }
    if (step.safety_notes) {
      sections.push(`<div class="details-section">
        <div class="details-label">Safety</div>
        <p>${this.esc(step.safety_notes)}</p>
      </div>`);
    }
    const urls = (step.video_urls && step.video_urls.length)
      ? step.video_urls
      : (step.video_url ? [step.video_url] : []);
    if (urls.length) {
      const videoHtml = urls.map(u => {
        const embedUrl = this._youtubeEmbedUrl(u);
        if (embedUrl) {
          return `<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;background:#000;margin-bottom:8px;">
            <iframe src="${embedUrl}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen loading="lazy"></iframe>
          </div>`;
        }
        return `<a href="${this.esc(u)}" target="_blank" rel="noopener">▶ Watch video</a>`;
      }).join('');
      sections.push(`<div class="details-section">${videoHtml}</div>`);
    }

    const body = sections.length
      ? sections.join('')
      : '<p class="details-empty">No coaching notes for this exercise yet.</p>';

    return `<div class="step-details-panel" id="details-panel-${idx}" hidden>${body}</div>`;
  }

  renderInfoButtons(step, idx) {
    return `
      <div class="exercise-info-btns">
        <button class="details-toggle-btn" data-step="${idx}">Details ▼</button>
      </div>
      ${this.renderDetailsPanel(step, idx)}
    `;
  }

  // ─── Prescription builders ────────────────────────────────────────────────

  buildWeightedPrescription(step) {
    const lines = [];

    const sets = parseInt(step.sets, 10);
    if (sets > 0) {
      let line = `${sets} ${sets === 1 ? 'set' : 'sets'}`;
      if (step.reps)                    line += ` × ${step.reps} reps`;
      if (parseFloat(step.load_kg) > 0) line += ` @ ${this.formatLoad(step.load_kg, step)}`;
      lines.push(line);
    }

    const restTempo = [];
    if (parseInt(step.rest_seconds, 10) > 0) restTempo.push(`Rest: ${step.rest_seconds}s`);
    if (step.tempo_pattern) {
      restTempo.push(`Tempo: ${this.formatPattern(step.tempo_pattern)} <span class="tempo-guide">(down · pause · up · pause)</span>`);
    }
    if (restTempo.length) lines.push(restTempo.join('  •  '));


    // Weight recommendation
    const recLoad   = parseFloat(step.recommended_load_kg);
    const recSource = step.recommendation_source;
    const recNote   = step.recommendation_note;
    // Only show recommendation info for load-based exercises, not bodyweight
    const isLoadExercise = parseFloat(step.load_kg) > 0
      || parseFloat(step.load_start_kg) > 0
      || parseFloat(step.load_peak_kg) > 0
      || recLoad > 0;
    if (recSource === 'no_data' && isLoadExercise) {
      lines.push(`<span class="rec-no-data">No recommendation — set your own weight</span>`);
    } else if (recLoad > 0 && recSource && recSource !== 'prescribed') {
      lines.push(
        `<span class="rec-load">Recommended: ${this.formatLoad(recLoad, step)}</span>` +
        (recNote ? `  <span class="rec-note">${this.esc(recNote)}</span>` : '')
      );
    }

    return this.wrapPrescription(lines, step.notes_coach);
  }

  buildSimplePrescription(step) {
    const lines = [];

    const sets = parseInt(step.sets, 10);
    if (sets > 0) {
      let line = `${sets} ${sets === 1 ? 'set' : 'sets'}`;
      if (step.reps)                    line += ` × ${step.reps} reps`;
      if (parseFloat(step.load_kg) > 0) line += ` @ ${this.formatLoad(step.load_kg, step)}`;
      lines.push(line);
    } else if (step.duration_value) {
      lines.push(`${step.duration_value} ${this.esc(step.duration_type) || 'min'}`);
    }

    if (parseInt(step.rest_seconds, 10) > 0) lines.push(`Rest: ${step.rest_seconds}s`);
    if (step.tempo_pattern) {
      lines.push(`Tempo: ${this.formatPattern(step.tempo_pattern)} <span class="tempo-guide">(down · pause · up · pause)</span>`);
    }

    return this.wrapPrescription(lines, step.notes_coach);
  }

  buildIntervalPrescription(step) {
    const lines = [];

    const count   = parseInt(step.interval_count, 10);
    const workSec = parseInt(step.interval_work_sec, 10);
    const restSec = parseInt(step.interval_rest_sec, 10);

    if (count > 0 && workSec > 0) {
      let line = `${count} rounds × ${workSec}s on`;
      if (restSec > 0) line += ` / ${restSec}s rest`;
      lines.push(line);
    } else if (step.duration_value) {
      lines.push(`${step.duration_value} ${this.esc(step.duration_type) || 'min'}`);
    }

    if (step.intensity_start || step.intensity_end) {
      lines.push(`Intensity: ${step.intensity_start || '—'} → ${step.intensity_end || '—'}`);
    }

    if (step.target_type || step.target_value) {
      const t = [step.target_type, step.target_value].filter(Boolean).map(s => this.esc(s)).join(': ');
      lines.push(`Target: ${t}`);
    }

    return this.wrapPrescription(lines, step.notes_coach);
  }

  wrapPrescription(lines, coachNotes) {
    const bodyHtml  = lines.map(l => `<div class="prescription-line">${l}</div>`).join('');
    const coachHtml = coachNotes
      ? `<div class="prescription-coach">📋 ${this.esc(coachNotes)}</div>`
      : '';
    if (!bodyHtml && !coachHtml) return '';
    return `<div class="prescription-block">${bodyHtml}${coachHtml}</div>`;
  }

  // ─── Rest timer ───────────────────────────────────────────────────────────

  renderRestTimer(step, idx) {
    const secs = parseInt(step.rest_seconds, 10);
    if (!secs || secs <= 0) return '';
    return `
      <div class="rest-timer" id="rest-timer-${idx}">
        <span class="rest-timer-label">Rest</span>
        <span class="rest-timer-display" id="rest-display-${idx}">${this.fmtTime(secs)}</span>
        <button class="rest-timer-btn" id="rest-btn-${idx}"
                data-step="${idx}" data-seconds="${secs}">▶ Start</button>
      </div>
    `;
  }

  fmtTime(secs) {
    if (secs < 60) return `${secs}s`;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  startRestTimer(stepIdx, totalSecs) {
    // Clear any existing timer for this step
    this.stopRestTimer(stepIdx);

    this.restRemaining[stepIdx] = totalSecs;

    const displayEl = document.getElementById(`rest-display-${stepIdx}`);
    const btnEl     = document.getElementById(`rest-btn-${stepIdx}`);
    const timerEl   = document.getElementById(`rest-timer-${stepIdx}`);

    if (btnEl) btnEl.textContent = '✕ Stop';
    if (timerEl) timerEl.classList.add('running');

    this.restTimers[stepIdx] = setInterval(() => {
      this.restRemaining[stepIdx]--;
      const rem = this.restRemaining[stepIdx];

      if (displayEl) displayEl.textContent = this.fmtTime(rem);

      if (rem <= 0) {
        this.stopRestTimer(stepIdx);
        if (displayEl) displayEl.textContent = 'Go!';
        if (timerEl) {
          timerEl.classList.remove('running');
          timerEl.classList.add('done');
          setTimeout(() => timerEl.classList.remove('done'), 2500);
        }
        if (btnEl) {
          btnEl.textContent = '▶ Start';
          btnEl.dataset.seconds = totalSecs;
        }
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
      }
    }, 1000);
  }

  stopRestTimer(stepIdx) {
    if (this.restTimers[stepIdx]) {
      clearInterval(this.restTimers[stepIdx]);
      delete this.restTimers[stepIdx];
    }
    const totalSecs = parseInt(
      document.getElementById(`rest-btn-${stepIdx}`)?.dataset.seconds || 0, 10
    );
    const displayEl = document.getElementById(`rest-display-${stepIdx}`);
    const btnEl     = document.getElementById(`rest-btn-${stepIdx}`);
    const timerEl   = document.getElementById(`rest-timer-${stepIdx}`);

    if (displayEl && totalSecs) displayEl.textContent = this.fmtTime(totalSecs);
    if (btnEl) btnEl.textContent = '▶ Start';
    if (timerEl) timerEl.classList.remove('running');
  }

  // ─── Exercise info modal ──────────────────────────────────────────────────

  showExerciseInfo(idx) {
    const step = this.steps[idx];
    if (!step) return;

    document.getElementById('ex-modal-title').textContent = step.exercise_name || 'Exercise';

    const sections = [];

    // Video embed / carousel
    const urls = (step.video_urls && step.video_urls.length) ? step.video_urls
               : (step.video_url ? [step.video_url] : []);
    if (urls.length > 1) {
      sections.push(this._renderVideoCarousel(urls));
    } else if (urls.length === 1) {
      const embedUrl = this._youtubeEmbedUrl(urls[0]);
      if (embedUrl) {
        sections.push(`<div class="ex-modal-section"><div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;background:#000;"><iframe src="${embedUrl}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div></div>`);
      }
    }

    if (step.equipment) {
      sections.push(`<div class="ex-modal-section"><h4>Equipment</h4><p>${this.esc(step.equipment)}</p></div>`);
    }
    if (step.exercise_description_long) {
      sections.push(`<div class="ex-modal-section"><h4>Description</h4><p>${this.esc(step.exercise_description_long)}</p></div>`);
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

    document.getElementById('ex-modal-body').innerHTML = sections.join('') || '<p class="text-muted">No additional details available.</p>';

    const modal = document.getElementById('ex-modal');
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  closeExerciseModal() {
    document.getElementById('ex-modal').hidden = true;
    document.body.style.overflow = '';
  }

  // ─── Utilities ────────────────────────────────────────────────────────────

  getDefaultMetric(step) {
    const key     = (step.metric_key || '').toLowerCase();
    const context = (step.metric_context_key || '').toLowerCase();
    const name    = (step.exercise_name || '').toLowerCase();
    const family  = (step.metric_family_default || '').toLowerCase();

    // Library join provides metric_family_default — use it first as the most reliable signal
    if (family === 'strength')          return 'kg';
    if (family === 'distance')          return 'm';
    if (family === 'duration' || family === 'time') return 'min';
    if (family === 'power')             return 'w';

    // Fall back to metric_key / context hints from Plans_Steps
    if (key.includes('kg') || key.includes('load') || context.includes('load')) return 'kg';
    if (key.includes('lb'))  return 'lb';
    if (key.includes('km'))  return 'km';
    if (key.includes('sec') || key.includes('time') || context.includes('time')) return 'sec';
    if (key.includes('min')) return 'min';
    if (key.includes('w') || key.includes('power') || context.includes('power')) return 'w';
    if (key.includes('cal')) return 'cal';
    if (key.includes('m') || key.includes('distance') || context.includes('distance')) return 'm';

    // Name-based cardio detection — exclude strength movements that contain cardio words
    // ('row' in Barbell Bent-Over Row, etc.)
    const isCardio = name.includes('run') || name.includes('swim') || name.includes('bike')
      || (name.includes('row') && !name.includes('barbell') && !name.includes('dumbbell')
          && !name.includes('cable') && !name.includes('bent'));
    if (isCardio) return 'm';

    return 'kg';
  }

  getValueLabel(metric) {
    const map = { kg: 'Weight', lb: 'Weight', sec: 'Time', min: 'Time', m: 'Distance', km: 'Distance', w: 'Power', cal: 'Cals', reps: 'Reps' };
    return map[metric] || 'Value';
  }

  metricOptions(defaultMetric) {
    return [
      { value: 'kg',   label: 'kg' },
      { value: 'lb',   label: 'lb' },
      { value: 'reps', label: 'reps (bodyweight)' },
      { value: 'sec',  label: 'seconds' },
      { value: 'min',  label: 'minutes' },
      { value: 'm',    label: 'metres' },
      { value: 'km',   label: 'km' },
      { value: 'w',    label: 'watts' },
      { value: 'cal',  label: 'cals' },
    ].map(o =>
      `<option value="${o.value}" ${o.value === defaultMetric ? 'selected' : ''}>${o.label}</option>`
    ).join('');
  }

  isDualDumbbell(step) {
    return String(step.special_flags || '').toLowerCase().includes('dual_dumbbell');
  }

  // Returns "30kg (15kg per dumbbell)" for dual-dumbbell exercises, "30kg" otherwise.
  formatLoad(kg, step) {
    const total = parseFloat(kg);
    if (!total) return '';
    if (this.isDualDumbbell(step)) {
      const perSide = total % 2 === 0 ? total / 2 : (total / 2).toFixed(1);
      return `${total}kg (${perSide}kg per dumbbell)`;
    }
    return `${total}kg`;
  }

  // Normalise an RPE value for display in a small input placeholder.
  // Strips leading "RPE " or "rpe " prefix so "RPE 8" → "8", "7-8" stays "7-8".
  _normalizeRpe(val) {
    if (val === null || val === undefined || val === '') return '';
    return String(val).replace(/^rpe\s*/i, '').trim();
  }

  esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(String(str)));
    return d.innerHTML;
  }

  _youtubeEmbedUrl(url) {
    if (!url) return null;
    const match = String(url).match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    return match ? `https://www.youtube.com/embed/${match[1]}` : null;
  }

  _renderVideoCarousel(urls) {
    const embedUrl = this._youtubeEmbedUrl(urls[0]);
    const firstVideo = embedUrl
      ? `<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;background:#000;"><iframe src="${embedUrl}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>`
      : `<p><a href="${this.esc(urls[0])}" target="_blank" rel="noopener" style="color:var(--bill-primary-light);">▶ Watch Video</a></p>`;
    const dots = urls.map((_, i) => `<span class="vid-dot${i === 0 ? ' active' : ''}"></span>`).join('');
    return `
      <div class="ex-modal-section">
        <div class="video-carousel" data-urls='${JSON.stringify(urls).replace(/'/g, '&#39;')}' data-index="0">
          <div class="video-wrap">${firstVideo}</div>
          <div class="video-carousel-nav">
            <button class="vid-nav-btn" data-vid-nav="prev">&#8249;</button>
            <div class="vid-dots">${dots}</div>
            <button class="vid-nav-btn" data-vid-nav="next">&#8250;</button>
          </div>
        </div>
      </div>`;
  }

  // Format patterns for display with · separators, agnostic of input format.
  // "2010"     → "2 · 0 · 1 · 0"  (compact digits — each char is one value)
  // "2-0-1-0"  → "2 · 0 · 1 · 0"  (hyphen-separated)
  // "8,10,12"  → "8 · 10 · 12"    (comma-separated multi-digit values)
  // "8 6 6"    → "8 · 6 · 6"      (space-separated)
  formatPattern(str) {
    if (!str) return '';
    const s = String(str).trim();
    if (!s) return '';

    // If any separator character is present, split on it
    if (/[,\-\/\s]/.test(s)) {
      const parts = s.split(/[\s,\-\/]+/).filter(p => p.length > 0);
      if (parts.length > 1) return parts.join(' · ');
    }

    // Compact all-digit string — each character is its own value
    if (/^\d+$/.test(s) && s.length > 1) {
      return s.split('').join(' · ');
    }

    return this.esc(s);
  }

  // ─── Events ───────────────────────────────────────────────────────────────

  bindEvents() {
    // Navigation
    const backBtn = document.getElementById('back-btn');
    if (backBtn) backBtn.addEventListener('click', () => window.location.href = '/session-preview.html');

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
    if (completeBtn) completeBtn.addEventListener('click', () => this.submitSession());

    // Glossary toggle
    const glossaryBtn   = document.getElementById('glossary-btn');
    const glossaryPanel = document.getElementById('glossary-panel');
    if (glossaryBtn && glossaryPanel) {
      glossaryBtn.addEventListener('click', () => {
        glossaryPanel.hidden = !glossaryPanel.hidden;
        glossaryBtn.textContent = glossaryPanel.hidden ? '📖 Terms' : '📖 Hide';
      });
    }

    // Exercise modal close
    document.getElementById('ex-modal-close').addEventListener('click', () => this.closeExerciseModal());
    document.getElementById('ex-modal').addEventListener('click', e => {
      if (e.target === e.currentTarget) this.closeExerciseModal();
    });

    // Video carousel navigation (delegated)
    document.getElementById('ex-modal-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-vid-nav]');
      if (!btn) return;
      const carousel = btn.closest('.video-carousel');
      if (!carousel) return;
      const urls = JSON.parse(carousel.dataset.urls);
      let idx = parseInt(carousel.dataset.index, 10);
      idx = btn.dataset.vidNav === 'prev'
        ? (idx - 1 + urls.length) % urls.length
        : (idx + 1) % urls.length;
      carousel.dataset.index = idx;
      const embedUrl = this._youtubeEmbedUrl(urls[idx]);
      const wrap = carousel.querySelector('.video-wrap');
      if (embedUrl) {
        wrap.innerHTML = `<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;background:#000;"><iframe src="${embedUrl}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>`;
      } else {
        wrap.innerHTML = `<p><a href="${this.esc(urls[idx])}" target="_blank" rel="noopener" style="color:var(--bill-primary-light);">▶ Watch Video</a></p>`;
      }
      carousel.querySelectorAll('.vid-dot').forEach((d, i) => d.classList.toggle('active', i === idx));
    });

    // Steps container: Add Set + metric change + details modal (event delegation)
    const container = document.getElementById('steps-container');

    container.addEventListener('click', e => {
      if (e.target.classList.contains('add-set-btn') && !e.target.disabled) {
        this.addSet(Number(e.target.dataset.step));
      }
      if (e.target.classList.contains('details-toggle-btn')) {
        this.toggleDetailsPanel(Number(e.target.dataset.step), e.target);
      }
      // Done-toggle: tap set number circle to confirm/unconfirm a set
      if (e.target.classList.contains('set-done-btn')) {
        const btn = e.target;
        const isDone = btn.dataset.done === 'true';
        btn.dataset.done = isDone ? 'false' : 'true';
        btn.classList.toggle('done', !isDone);
        btn.textContent = isDone ? btn.dataset.set : '✓';
      }
      if (e.target.classList.contains('rest-timer-btn')) {
        const stepIdx = Number(e.target.dataset.step);
        if (this.restTimers[stepIdx]) {
          // Timer running — stop and reset
          this.stopRestTimer(stepIdx);
        } else {
          // Start timer
          const secs = parseInt(e.target.dataset.seconds, 10);
          this.startRestTimer(stepIdx, secs);
        }
      }
    });

    // Any input in a set row auto-confirms that set
    container.addEventListener('input', e => {
      if (e.target.classList.contains('set-input')) {
        const row = e.target.closest('.set-row');
        if (!row) return;
        const btn = row.querySelector('.set-done-btn');
        if (btn && btn.dataset.done !== 'true') {
          btn.dataset.done = 'true';
          btn.classList.add('done');
          btn.textContent = '✓';
        }
      }
    });

    container.addEventListener('change', e => {
      if (e.target.classList.contains('exercise-metric-select')) {
        const card = e.target.closest('.exercise-step-card');
        if (card) {
          const header = card.querySelector('.value-label-header');
          if (header) header.textContent = this.getValueLabel(e.target.value);
        }
      }
    });
  }

  addSet(stepIdx) {
    const current = this.stepSetCounts[stepIdx];
    if (current >= 10) return;

    const newCount = current + 1;
    this.stepSetCounts[stepIdx] = newCount;

    const rowsEl = document.getElementById(`sets-rows-${stepIdx}`);
    if (rowsEl) {
      const step = this.steps[stepIdx];
      const mode = step ? this.getInputMode(step) : 'reps_load_rpe';
      const recLoad = step ? parseFloat(step.recommended_load_kg) || null : null;
      rowsEl.insertAdjacentHTML('beforeend', this.renderSetRow(stepIdx, newCount, mode, recLoad));
    }

    if (newCount >= 10) {
      const btn = document.querySelector(`.add-set-btn[data-step="${stepIdx}"]`);
      if (btn) btn.disabled = true;
    }
  }

  // ─── Data collection ──────────────────────────────────────────────────────

  collectStepUpdates() {
    const updates = [];

    document.querySelectorAll('.exercise-step-card').forEach(card => {
      const idx  = Number(card.dataset.stepIdx);
      const step = this.steps[idx];
      if (!step || !step.step_id) return;

      const update = { step_id: step.step_id };

      // Include metric keys + direction so Plans_Steps is self-contained for Exercise Bests matching
      if (step.metric_key)         update.metric_key         = step.metric_key;
      if (step.metric_context_key) update.metric_context_key = step.metric_context_key;
      if (step.better_direction)   update.better_direction   = step.better_direction;

      const metricSelect = card.querySelector('.exercise-metric-select');
      const metric       = metricSelect ? metricSelect.value : null;

      card.querySelectorAll('.set-row').forEach(row => {
        const doneBtn = row.querySelector('.set-done-btn');
        if (!doneBtn || doneBtn.dataset.done !== 'true') return; // skip unconfirmed sets

        const setNum     = row.dataset.setNum;
        const repsInput  = row.querySelector('[data-field-type="reps"]');
        const valueInput = row.querySelector('[data-field-type="value"]');
        const rpeInput   = row.querySelector('[data-field-type="rpe"]');

        // Use entered value; fall back to prescribed if input left blank
        const repsVal  = repsInput?.value?.trim()  || row.dataset.prescribedReps  || '';
        const loadVal  = valueInput?.value?.trim()  || row.dataset.prescribedLoad  || '';
        const rpeVal   = rpeInput?.value?.trim()    || row.dataset.prescribedRpe   || '';

        if (repsVal  !== '') update[`actual_set${setNum}_reps`]  = Number(repsVal);
        if (loadVal  !== '') {
          update[`actual_set${setNum}_value`]  = Number(loadVal);
          if (metric) update[`actual_set${setNum}_metric`] = metric;
        }
        if (rpeVal   !== '') update[`actual_set${setNum}_rpe`]   = Number(rpeVal);
      });

      const notesEl = card.querySelector('[data-field="notes_athlete"]');
      if (notesEl && notesEl.value.trim()) update.notes_athlete = notesEl.value.trim();

      // Deviation tracking — flag when actual load differs >15% from recommendation
      const recLoad   = parseFloat(step.recommended_load_kg);
      const recSource = step.recommendation_source;
      if (recLoad > 0 && recSource && recSource !== 'prescribed' && recSource !== 'no_data') {
        let totalLoad = 0, loadSetCount = 0;
        card.querySelectorAll('.set-row').forEach(row => {
          const doneBtn = row.querySelector('.set-done-btn');
          if (!doneBtn || doneBtn.dataset.done !== 'true') return;
          const valueInput = row.querySelector('[data-field-type="value"]');
          const loadVal = valueInput?.value?.trim() || row.dataset.prescribedLoad || '';
          if (loadVal !== '') {
            totalLoad += Number(loadVal);
            loadSetCount++;
          }
        });
        if (loadSetCount > 0) {
          const avgLoad = totalLoad / loadSetCount;
          const deviationPct = Math.abs(avgLoad - recLoad) / recLoad;
          if (deviationPct > 0.15) {
            update.recommended_load_kg      = recLoad;
            update.recommendation_source    = recSource;
            update.load_deviation_pct       = Math.round(deviationPct * 100);
            update.load_deviation_direction = avgLoad > recLoad ? 'above' : 'below';
            update.flag_for_bill            = true;
          }
        }
      }

      updates.push(update); // always include so status + timestamp gets written
    });

    return updates;
  }

  // ─── Submission ───────────────────────────────────────────────────────────

  async submitSession() {
    try {
      app.showLoading('Submitting session...');

      const steps = this.collectStepUpdates();
      const rpe   = document.getElementById('session-rpe').value;
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

      // Build summary for the complete screen before clearing storage
      const mainSteps = this.steps.filter(s => (s.segment_type || '').toLowerCase() === 'main');
      localStorage.setItem('bill_session_summary', JSON.stringify({
        focus:          this.session.focus || '',
        session_date:   this.session.session_date || '',
        location:       this.session.location || '',
        rpe:            rpe || '',
        notes:          notes || '',
        main_exercises: mainSteps.map(s => s.exercise_name).filter(Boolean),
        total_steps:    this.steps.length,
      }));

      localStorage.removeItem('active_session_steps');
      app.clearActiveSession();
      app.hideLoading();
      window.location.href = '/session-complete.html';
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
