// Bill D'Bettabody - Chat Logic

const THINKING_MESSAGES = [
  'Thinking...',
  'Processing...',
  'Checking your data...',
  'Preparing response...',
  'Working on it...',
  'Almost there...',
];

class Chat {
  constructor() {
    this.messagesEl = null;
    this.inputEl = null;
    this.sendBtn = null;
    this.statusEl = null;
    this.isLoading = false;
    this._thinkingInterval = null;
    this._thinkingIndex = 0;
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

    // New user discovery — auto-trigger Bill's intro instead of static greeting
    const isNewUser = localStorage.getItem('bill_new_user_intro') === 'true';
    if (isNewUser) {
      localStorage.removeItem('bill_new_user_intro');
      await this.triggerNewUserIntro();
    } else {
      // Existing user — show pre-generated greeting
      const greeting = localStorage.getItem('bill_greeting')
        || "Right then. What do you need?";
      this.addMessage('bill', greeting);
    }

    this.inputEl.focus();
  }

  async triggerNewUserIntro() {
    // Send a silent trigger to the API — don't show it as a user message.
    // Bill opens the conversation explaining who he is and how to get started.
    this.isLoading = true;
    this.sendBtn.disabled = true;
    this.inputEl.disabled = true;
    this.startThinking();
    this.showTyping();

    const trigger = [
      '[CONTEXT: New user discovery session. No client profile exists.',
      'The user tapped "New here? Get Started" on the login screen',
      'and has been connected directly to you without a Client ID.]',
      '',
      'Hi Bill — I\'m completely new here. Can you tell me who you are,',
      'what you do as a coach, what this app offers, and how I\'d go',
      'about getting properly set up with you?',
    ].join(' ');

    try {
      const result = await api.chat(trigger, app.sessionId);
      this.hideTyping();
      this.stopThinking();
      if (result && result.response) {
        this.addMessage('bill', result.response);
      } else {
        this.addMessage('bill', "Right then — I'm Bill D'Bettabody. Something went a bit sideways just now, but fire away.");
      }
    } catch (err) {
      console.error('[Chat] New user intro failed:', err);
      this.hideTyping();
      this.stopThinking();
      this.addMessage('bill', "Right then. I'm Bill. Tell me what you're after and we'll take it from there.");
    } finally {
      this.isLoading = false;
      this.sendBtn.disabled = false;
      this.inputEl.disabled = false;
    }
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

  startThinking() {
    this._thinkingIndex = 0;
    this.setStatus(THINKING_MESSAGES[0], 'var(--bill-warning)');
    this._thinkingInterval = setInterval(() => {
      this._thinkingIndex = (this._thinkingIndex + 1) % THINKING_MESSAGES.length;
      this.setStatus(THINKING_MESSAGES[this._thinkingIndex], 'var(--bill-warning)');
    }, 2000);
  }

  stopThinking() {
    if (this._thinkingInterval) {
      clearInterval(this._thinkingInterval);
      this._thinkingInterval = null;
    }
    this.setStatus('Online', 'var(--bill-success)');
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
    this.startThinking();

    this.showTyping();

    try {
      const result = await api.chat(text, app.sessionId);
      this.hideTyping();
      this.stopThinking();

      if (result && result.response) {
        this.addMessage('bill', result.response);
      } else {
        this.addMessage('bill', "Something went wrong on my end. Try again.");
      }
    } catch (error) {
      console.error('[Chat] Request failed:', error);
      this.hideTyping();
      this.stopThinking();
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
