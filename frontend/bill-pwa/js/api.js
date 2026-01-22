// Bill D'Bettabody - API Client
// Handles all backend communication
// Currently uses mock data, easy to swap for real API

const API_CONFIG = {
  // Switch this to your backend URL when ready
  BASE_URL: 'http://localhost:5000',
  USE_MOCK_DATA: true, // Set to false when backend is ready
  TIMEOUT: 30000
};

class BillAPI {
  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
    this.useMock = API_CONFIG.USE_MOCK_DATA;
  }

  // Helper: Make API request
  async request(endpoint, options = {}) {
    // Use mock data if enabled
    if (this.useMock) {
      return this.mockRequest(endpoint, options);
    }

    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[API] Request failed:', error);
      throw error;
    }
  }

  // Mock request handler
  async mockRequest(endpoint, options = {}) {
    console.log('[API] Mock request:', endpoint, options.method || 'GET');
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300));

    // Get mock data
    const data = getMockData(endpoint);
    
    if (!data) {
      throw new Error(`Mock data not found for: ${endpoint}`);
    }

    return data;
  }

  // Session endpoints
  async getTodaySession() {
    return this.request('/sessions/today');
  }

  async getSessionSteps(sessionId) {
    return this.request(`/sessions/${sessionId}/steps`);
  }

  async logStep(sessionId, stepData) {
    return this.request(`/sessions/${sessionId}/log-step`, {
      method: 'POST',
      body: JSON.stringify(stepData)
    });
  }

  async addExtraExercise(sessionId, exerciseData) {
    return this.request(`/sessions/${sessionId}/add-exercise`, {
      method: 'POST',
      body: JSON.stringify(exerciseData)
    });
  }

  async completeSession(sessionId, completionData) {
    return this.request(`/sessions/${sessionId}/complete`, {
      method: 'POST',
      body: JSON.stringify(completionData)
    });
  }

  // Profile & nutrition
  async getProfile() {
    return this.request('/profile');
  }

  async getDailyNutrition() {
    return this.request('/nutrition/daily');
  }

  // Exercise bests
  async getBests() {
    return this.request('/bests');
  }

  // Exercise library
  async searchExercises(query) {
    return this.request(`/exercises/search?q=${encodeURIComponent(query)}`);
  }

  async getExerciseDetail(exerciseName) {
    return this.request(`/exercises/${encodeURIComponent(exerciseName)}`);
  }

  // Chat
  async chat(message, sessionId) {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId })
    });
  }

  // Initialize session
  async initialize(clientId = null) {
    return this.request('/initialize', {
      method: 'POST',
      body: JSON.stringify({ client_id: clientId })
    });
  }
}

// Create global API instance
const api = new BillAPI();
