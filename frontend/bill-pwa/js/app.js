// Bill D'Bettabody - Core App Logic
// Handles initialization, routing, and session management

class BillApp {
  constructor() {
    this.sessionId = null;
    this.clientId = null;
    this.activeSession = null;
    this.currentStep = null;
  }

  // Initialize app
  async init() {
    console.log('[App] Initializing Bill D\'Bettabody PWA');

    // Register service worker
    if ('serviceWorker' in navigator) {
      try {
        await navigator.serviceWorker.register('/sw.js');
        console.log('[App] Service worker registered');
      } catch (error) {
        console.error('[App] Service worker registration failed:', error);
      }
    }

    // Check for existing session
    this.loadSession();

    // Set up navigation
    this.setupNavigation();

    console.log('[App] Initialized successfully');
  }

  // Load session from localStorage
  loadSession() {
    const stored = localStorage.getItem('bill_session');
    
    if (stored) {
      try {
        const session = JSON.parse(stored);
        this.sessionId = session.session_id;
        this.clientId = session.client_id;
        console.log('[App] Loaded session:', this.clientId);
      } catch (error) {
        console.error('[App] Failed to load session:', error);
        localStorage.removeItem('bill_session');
      }
    }
  }

  // Save session to localStorage
  saveSession(sessionData) {
    this.sessionId = sessionData.session_id;
    this.clientId = sessionData.client_id;
    
    localStorage.setItem('bill_session', JSON.stringify({
      session_id: this.sessionId,
      client_id: this.clientId,
      created_at: new Date().toISOString()
    }));
    
    console.log('[App] Session saved');
  }

  // Clear session
  clearSession() {
    this.sessionId = null;
    this.clientId = null;
    this.activeSession = null;
    localStorage.removeItem('bill_session');
    console.log('[App] Session cleared');
  }

  // Navigation setup
  setupNavigation() {
    // Handle back button
    window.addEventListener('popstate', (event) => {
      if (event.state && event.state.page) {
        this.navigateTo(event.state.page, false);
      }
    });
  }

  // Navigate to page
  navigateTo(page, pushState = true) {
    console.log('[App] Navigating to:', page);
    
    if (pushState) {
      history.pushState({ page }, '', `/${page}`);
    }

    // Emit custom event for page changes
    window.dispatchEvent(new CustomEvent('bill:navigate', { 
      detail: { page } 
    }));
  }

  // Session management
  setActiveSession(sessionData) {
    this.activeSession = sessionData;
    localStorage.setItem('bill_active_session', JSON.stringify(sessionData));
  }

  getActiveSession() {
    if (this.activeSession) {
      return this.activeSession;
    }

    const stored = localStorage.getItem('bill_active_session');
    if (stored) {
      try {
        this.activeSession = JSON.parse(stored);
        return this.activeSession;
      } catch (error) {
        console.error('[App] Failed to load active session:', error);
      }
    }

    return null;
  }

  clearActiveSession() {
    this.activeSession = null;
    localStorage.removeItem('bill_active_session');
  }

  // Step tracking (for active session)
  setCurrentStep(stepData) {
    this.currentStep = stepData;
    localStorage.setItem('bill_current_step', JSON.stringify(stepData));
  }

  getCurrentStep() {
    if (this.currentStep) {
      return this.currentStep;
    }

    const stored = localStorage.getItem('bill_current_step');
    if (stored) {
      try {
        this.currentStep = JSON.parse(stored);
        return this.currentStep;
      } catch (error) {
        console.error('[App] Failed to load current step:', error);
      }
    }

    return null;
  }

  clearCurrentStep() {
    this.currentStep = null;
    localStorage.removeItem('bill_current_step');
  }

  // Utility: Format date
  formatDate(dateString) {
    const date = new Date(dateString);
    const options = { weekday: 'long', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-GB', options);
  }

  // Utility: Format time
  formatTime(minutes) {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }

  // Utility: Show loading indicator
  showLoading(message = 'Loading...') {
    // Simple loading indicator - enhance later
    const existing = document.getElementById('bill-loading');
    if (existing) existing.remove();

    const loader = document.createElement('div');
    loader.id = 'bill-loading';
    loader.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    loader.innerHTML = `
      <div class="bg-white rounded-lg p-6 shadow-xl">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-800 mx-auto mb-4"></div>
        <p class="text-gray-700 font-medium">${message}</p>
      </div>
    `;
    document.body.appendChild(loader);
  }

  hideLoading() {
    const loader = document.getElementById('bill-loading');
    if (loader) loader.remove();
  }

  // Utility: Show error
  showError(message) {
    alert(`Error: ${message}`); // Simple for now, enhance later
  }
}

// Create global app instance
const app = new BillApp();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => app.init());
} else {
  app.init();
}
