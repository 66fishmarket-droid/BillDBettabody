class ProgressScreen {

  constructor() {
    this.groups = [];
    this.expandedGroups = new Set();
  }

  async init() {
    await app.init();

    document.getElementById('back-btn').addEventListener('click', () => {
      window.location.href = '/dashboard.html';
    });

    await this.load();
  }

  async load() {
    if (!app.sessionId) {
      window.location.href = '/index.html';
      return;
    }

    try {
      app.showLoading('Loading your progress...');
      const data = await api.getProgress(app.sessionId);
      app.hideLoading();

      this.groups = data.groups || [];

      if (!this.groups.length) {
        document.getElementById('progress-empty').hidden = false;
        return;
      }

      this.render();
    } catch (err) {
      app.hideLoading();
      console.error('[Progress] Load failed:', err);
      // If session is invalid, redirect to login rather than showing a dead error
      if (err.message && err.message.includes('400')) {
        window.location.href = '/index.html';
        return;
      }
      app.showError('Could not load progress data. Please try again.');
    }
  }

  render() {
    const container = document.getElementById('progress-container');
    container.innerHTML = this.groups.map((g, idx) => this.renderGroup(g, idx)).join('');

    // Accordion toggle
    container.querySelectorAll('.prog-group-header').forEach(header => {
      header.addEventListener('click', () => {
        const idx   = parseInt(header.dataset.group, 10);
        const body  = document.getElementById(`prog-group-body-${idx}`);
        const arrow = header.querySelector('.prog-group-arrow');

        if (this.expandedGroups.has(idx)) {
          this.expandedGroups.delete(idx);
          body.hidden  = true;
          arrow.textContent = '›';
        } else {
          this.expandedGroups.add(idx);
          body.hidden  = false;
          arrow.textContent = '▾';
        }
      });
    });
  }

  renderGroup(group, idx) {
    const pct     = group.avg_improvement_pct;
    const pctText = pct != null ? this.formatPct(pct) : '—';
    const pctCls  = pct != null && pct >= 0 ? 'prog-pct positive' : 'prog-pct negative';

    return `
      <div class="card mb-3 prog-group-card">
        <div class="prog-group-header" data-group="${idx}">
          <div class="prog-group-info">
            <span class="prog-group-name">${this.esc(group.name)}</span>
            <span class="prog-group-meta">${group.exercise_count} exercise${group.exercise_count !== 1 ? 's' : ''}</span>
          </div>
          <div class="prog-group-right">
            <span class="${pctCls}">${pctText}</span>
            <span class="prog-group-arrow">›</span>
          </div>
        </div>

        <div class="prog-group-body" id="prog-group-body-${idx}" hidden>
          ${group.exercises.map(e => this.renderExercise(e)).join('')}
        </div>
      </div>
    `;
  }

  renderExercise(ex) {
    const unit         = ex.unit ? ` ${ex.unit}` : '';
    const bestVal      = ex.best_value;
    const firstVal     = ex.first_value;
    const recentVal    = ex.recent_value;
    const pct          = ex.improvement_pct;
    const pctText      = pct != null ? this.formatPct(pct) : '';
    const pctCls       = pct != null && pct >= 0 ? 'prog-pct positive' : 'prog-pct negative';

    // Bar widths scaled to best_value (100%)
    const firstPct  = bestVal && firstVal  != null ? Math.round((firstVal  / bestVal) * 100) : 0;
    const recentPct = bestVal && recentVal != null ? Math.round((recentVal / bestVal) * 100) : null;

    const recentRow = recentPct != null ? `
      <div class="prog-bar-row">
        <span class="prog-bar-label">Recent</span>
        <span class="prog-bar-value">${this.fmt(recentVal)}${unit}</span>
        <div class="prog-bar-track">
          <div class="prog-bar-fill recent" style="width:${recentPct}%"></div>
        </div>
      </div>` : '';

    const sessions = ex.session_count ? `${ex.session_count} session${ex.session_count != 1 ? 's' : ''}` : '';

    return `
      <div class="prog-exercise">
        <div class="prog-exercise-header">
          <span class="prog-exercise-name">${this.esc(ex.exercise_name)}</span>
          ${pctText ? `<span class="${pctCls}">${pctText}</span>` : ''}
        </div>

        <div class="prog-bars">
          <div class="prog-bar-row">
            <span class="prog-bar-label">Started</span>
            <span class="prog-bar-value">${this.fmt(firstVal)}${unit}</span>
            <div class="prog-bar-track">
              <div class="prog-bar-fill started" style="width:${firstPct}%"></div>
            </div>
          </div>

          ${recentRow}

          <div class="prog-bar-row">
            <span class="prog-bar-label">Best</span>
            <span class="prog-bar-value">${this.fmt(bestVal)}${unit}</span>
            <div class="prog-bar-track">
              <div class="prog-bar-fill best" style="width:100%"></div>
            </div>
          </div>
        </div>

        ${sessions ? `<p class="prog-exercise-meta">${sessions}</p>` : ''}
      </div>
    `;
  }

  formatPct(pct) {
    return pct >= 0 ? `+${pct}%` : `${pct}%`;
  }

  fmt(val) {
    if (val == null) return '—';
    // Drop trailing .0 for whole numbers
    return Number.isInteger(val) ? val : parseFloat(val.toFixed(2));
  }

  esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

const progressScreen = new ProgressScreen();
document.addEventListener('DOMContentLoaded', () => progressScreen.init());
