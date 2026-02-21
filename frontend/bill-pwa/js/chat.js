// Bill D'Bettabody - Chat Logic

class Chat {
  constructor() {
    this.messagesEl = null;
    this.inputEl = null;
    this.sendBtn = null;
    this.statusEl = null;
    this.isLoading = false;
  }

  async init() {
    console.log('[Chat] Initializing...');

    // Redirect if no session
    if (!app.sessionId) {
      console.warn('[Chat] No session found — redirecting to login');
      window.location.href = '/index.html';
      return;
    }

    this.messagesEl = document.getElementById('chat-messages');
    this.inputEl = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('send-btn');
    this.statusEl = document.getElementById('bill-status');

    this.setupEventListeners();

    // Show Bill's greeting as first message
    const greeting = localStorage.getItem('bill_greeting')
      || "Right then. What do you need?";
    this.addMessage('bill', greeting);

    // Focus input
    this.inputEl.focus();
  }

  setupEventListeners() {
    // Back button
    document.getElementById('back-btn').addEventListener('click', () => {
      window.location.href = '/dashboard.html';
    });

    // Send on button click
    this.sendBtn.addEventListener('click', () => this.sendMessage());

    // Send on Enter (Shift+Enter = newline)
    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto-resize textarea
    this.inputEl.addEventListener('input', () => {
      this.inputEl.style.height = 'auto';
      this.inputEl.style.height = `${Math.min(this.inputEl.scrollHeight, 120)}px`;
    });
  }

  addMessage(role, text) {
    const msgEl = document.createElement('div');
    msgEl.className = `chat-message ${role}`;

    const label = role === 'bill' ? 'Bill' : 'You';

    msgEl.innerHTML = `
      <span class="chat-message-label">${label}</span>
      <div class="chat-bubble">${this.escapeHtml(text)}</div>
    `;

    this.messagesEl.appendChild(msgEl);
    this.scrollToBottom();
  }

  showTyping() {
    const el = document.createElement('div');
    el.id = 'typing-indicator-msg';
    el.className = 'chat-message bill';
    el.innerHTML = `
      <span class="chat-message-label">Bill</span>
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    `;
    this.messagesEl.appendChild(el);
    this.scrollToBottom();
  }

  hideTyping() {
    const el = document.getElementById('typing-indicator-msg');
    if (el) el.remove();
  }

  setStatus(text, color) {
    if (this.statusEl) {
      this.statusEl.textContent = text;
      this.statusEl.style.color = color || '';
    }
  }

  scrollToBottom() {
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  async sendMessage() {
    const text = this.inputEl.value.trim();
    if (!text || this.isLoading) return;

    // Clear input and reset height
    this.inputEl.value = '';
    this.inputEl.style.height = 'auto';

    // Show user message
    this.addMessage('user', text);

    // Lock UI
    this.isLoading = true;
    this.sendBtn.disabled = true;
    this.inputEl.disabled = true;
    this.setStatus('Thinking...', 'var(--bill-warning)');

    this.showTyping();

    try {
      const result = await api.chat(text, app.sessionId);
      this.hideTyping();
      this.setStatus('Online', 'var(--bill-success)');

      if (result && result.response) {
        this.addMessage('bill', result.response);
      } else {
        this.addMessage('bill', "Something went wrong on my end. Try again.");
      }
    } catch (error) {
      console.error('[Chat] Request failed:', error);
      this.hideTyping();
      this.setStatus('Online', 'var(--bill-success)');
      this.addMessage('bill', "Right, something broke. Give it another go.");
    } finally {
      this.isLoading = false;
      this.sendBtn.disabled = false;
      this.inputEl.disabled = false;
      this.inputEl.focus();
    }
  }
}

const chat = new Chat();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => chat.init());
} else {
  chat.init();
}
