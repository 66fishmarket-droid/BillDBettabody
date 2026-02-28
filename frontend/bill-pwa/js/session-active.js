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

  // ─── Step classification ──────────────────────────────────────────────────

  // Main-segment exercises that get per-set/per-round logging
  isWeightedStep(step) {
    if ((step.segment_type || '').toLowerCase() !== 'main') return false;
    return parseInt(step.sets, 10) > 0 || parseInt(step.interval_count, 10) > 0;
  }

  isIntervalStep(step) {
    return parseInt(step.interval_count, 10) > 0 || parseInt(step.interval_work_sec, 10) > 0;
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
    const isInterval  = this.isIntervalStep(step);
    const setCount    = this.stepSetCounts[idx];
    const metric      = this.getDefaultMetric(step);
    const valueLabel  = this.getValueLabel(metric);
    const repsHeader  = isInterval ? 'Round' : 'Reps';
    const prescription = isInterval
      ? this.buildIntervalPrescription(step)
      : this.buildWeightedPrescription(step);

    return `
      <div class="card mb-3 exercise-step-card" data-step-idx="${idx}">
        <div class="step-segment-tag segment-main">Main</div>
        <div class="step-exercise-name">${this.esc(step.exercise_name) || 'Exercise'}</div>
        ${step.exercise_description_short ? `<div class="step-exercise-desc">${this.esc(step.exercise_description_short)}</div>` : ''}
        ${prescription}
        <div class="step-divider"></div>

        <div class="sets-header">
          <span></span>
          <span>${repsHeader}</span>
          <span class="value-label-header">${valueLabel}</span>
          <span>RPE</span>
        </div>

        <div class="sets-rows" id="sets-rows-${idx}">
          ${Array.from({ length: setCount }, (_, i) => this.renderSetRow(idx, i + 1)).join('')}
        </div>

        ${this.renderRestTimer(step, idx)}

        <div class="step-actions-row">
          <div>
            <button class="add-set-btn" data-step="${idx}" ${setCount >= 10 ? 'disabled' : ''}>
              + Add Set
            </button>
            <div class="add-set-hint">add warm-up or extra sets</div>
          </div>
          <div class="metric-selector">
            <label>Unit:</label>
            <select class="exercise-metric-select" data-step="${idx}">
              ${this.metricOptions(metric)}
            </select>
          </div>
        </div>

        ${this.renderInfoButtons(step, idx)}

        <textarea data-step="${idx}" data-field="notes_athlete" rows="2"
                  class="step-notes-input"
                  placeholder="Notes (optional)...">${this.esc(step.notes_athlete) || ''}</textarea>
      </div>
    `;
  }

  renderSetRow(stepIdx, setNum) {
    return `
      <div class="set-row" data-set-num="${setNum}">
        <span class="set-num">${setNum}</span>
        <input class="set-input" type="number" min="0" inputmode="numeric" pattern="[0-9]*"
               data-step="${stepIdx}" data-set="${setNum}" data-field-type="reps" placeholder="—">
        <input class="set-input" type="number" min="0" step="0.5" inputmode="decimal" pattern="[0-9.]*"
               data-step="${stepIdx}" data-set="${setNum}" data-field-type="value" placeholder="—">
        <input class="set-input" type="number" min="1" max="10" inputmode="numeric" pattern="[0-9]*"
               data-step="${stepIdx}" data-set="${setNum}" data-field-type="rpe" placeholder="—">
      </div>
    `;
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

  renderInfoButtons(step, idx) {
    const hasVideo   = !!(step.video_url || (step.video_urls && step.video_urls.length));
    const hasDetails = !!(step.exercise_description_long || step.safety_notes || step.common_mistakes
                          || step.regression || step.progression || step.equipment);
    if (!hasVideo && !hasDetails) return '';

    return `
      <div class="exercise-info-btns">
        <button class="exercise-info-btn details-btn" data-step="${idx}">📋 Extra Details</button>
      </div>
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

    if (step.pattern_type) {
      const p = [`Pattern: ${this.esc(step.pattern_type)}`];
      if (parseFloat(step.load_start_kg) > 0)    p.push(`Start: ${this.formatLoad(step.load_start_kg, step)}`);
      if (parseFloat(step.load_increment_kg) > 0) p.push(`+${step.load_increment_kg}kg/set`);
      if (parseFloat(step.load_peak_kg) > 0)      p.push(`Peak: ${this.formatLoad(step.load_peak_kg, step)}`);
      lines.push(p.join('  •  '));
    }

    if (step.reps_pattern)          lines.push(`Reps: ${this.formatPattern(step.reps_pattern)}`);
    if (step.rpe_pattern)           lines.push(`RPE target: ${this.formatPattern(step.rpe_pattern)}`);
    if (step.tempo_per_set_pattern) lines.push(`Tempo per set: ${this.formatPattern(step.tempo_per_set_pattern)}`);
    if (step.pattern_notes)         lines.push(`<em>${this.esc(step.pattern_notes)}</em>`);

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
      if (e.target.classList.contains('details-btn')) {
        this.showExerciseInfo(Number(e.target.dataset.step));
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
    if (rowsEl) rowsEl.insertAdjacentHTML('beforeend', this.renderSetRow(stepIdx, newCount));

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
        const setNum     = row.dataset.setNum;
        const repsInput  = row.querySelector('[data-field-type="reps"]');
        const valueInput = row.querySelector('[data-field-type="value"]');
        const rpeInput   = row.querySelector('[data-field-type="rpe"]');

        if (repsInput  && repsInput.value  !== '') update[`actual_set${setNum}_reps`]  = Number(repsInput.value);
        if (valueInput && valueInput.value !== '') {
          update[`actual_set${setNum}_value`]  = Number(valueInput.value);
          if (metric) update[`actual_set${setNum}_metric`] = metric;
        }
        if (rpeInput   && rpeInput.value   !== '') update[`actual_set${setNum}_rpe`]   = Number(rpeInput.value);
      });

      const notesEl = card.querySelector('[data-field="notes_athlete"]');
      if (notesEl && notesEl.value.trim()) update.notes_athlete = notesEl.value.trim();

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
