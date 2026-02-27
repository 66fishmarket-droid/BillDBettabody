// ─── Help Modal ───────────────────────────────────────────────────────────────
// Injects a shared bottom-sheet modal into the page and opens it with the
// FAQ content for the current page from help-content.js.
//
// Usage:
//   helpModal.open('dashboard')   // from a button's onclick
//
// To add FAQs: edit help-content.js only — no changes needed here.

class HelpModal {
  constructor() {
    this._inject();
    this._bind();
  }

  _inject() {
    const modal = document.createElement('div');
    modal.id = 'help-modal';
    modal.className = 'ex-modal-overlay';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="ex-modal-box">
        <div class="ex-modal-header">
          <strong id="help-modal-title">How to use this page</strong>
          <button id="help-modal-close" class="ex-modal-close" aria-label="Close">&#10005;</button>
        </div>
        <div id="help-modal-body" class="ex-modal-body help-faq-list"></div>
        <div class="help-modal-footer">
          <a href="/chat.html" class="help-ask-bill-btn">&#128172; Ask Bill a question</a>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }

  _bind() {
    const modal = document.getElementById('help-modal');

    document.getElementById('help-modal-close').addEventListener('click', () => this.close());

    modal.addEventListener('click', e => {
      if (e.target === modal) this.close();
    });

    // Accordion — delegated to modal body
    document.getElementById('help-modal-body').addEventListener('click', e => {
      const btn = e.target.closest('.help-faq-q');
      if (!btn) return;
      const item = btn.closest('.help-faq-item');
      const isOpen = item.classList.contains('open');
      // Close all, then open the tapped one (unless it was already open)
      document.querySelectorAll('.help-faq-item.open').forEach(el => el.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  }

  open(pageKey) {
    const content = (typeof HELP_CONTENT !== 'undefined') && HELP_CONTENT[pageKey];
    if (!content) {
      console.warn(`[HelpModal] No content found for page key: "${pageKey}"`);
      return;
    }

    document.getElementById('help-modal-title').textContent = content.title;
    document.getElementById('help-modal-body').innerHTML = content.faqs.map(faq => `
      <div class="help-faq-item">
        <button class="help-faq-q">
          <span>${faq.q}</span>
          <span class="help-faq-chevron">&#8250;</span>
        </button>
        <div class="help-faq-a"><p>${faq.a}</p></div>
      </div>`).join('');

    // Reset scroll and open state
    document.getElementById('help-modal-body').scrollTop = 0;
    document.getElementById('help-modal').hidden = false;
    document.body.style.overflow = 'hidden';
  }

  close() {
    document.getElementById('help-modal').hidden = true;
    document.body.style.overflow = '';
  }
}

const helpModal = new HelpModal();
