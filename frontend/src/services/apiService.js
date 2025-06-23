
const API_BASE_URL = 'http://localhost:5000';
console.log(API_BASE_URL)

export const apiService = {
  async request(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}/api${endpoint}`, {  
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Network error' }));
      throw new Error(error.error || 'Request failed');
    }
    
    return response.json();
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/api/upload`, {  // Fixed: Added /api prefix
      method: 'POST',
      credentials: 'include',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Upload failed' }));
      throw new Error(error.error || 'Upload failed');
    }
    
    return response.json();
  },

  async analyzeUrl(url) {
    return this.request('/analyze-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  },

  async summarize() {
    return this.request('/summarize', {
      method: 'POST',
    });
  },

  async askQuestion(question) {
    return this.request('/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    });
  },

  async getSuggestedQuestions() {
    return this.request('/suggested-questions', {
      method: 'POST',
    });
  },

  async getStatus() {
    return this.request('/status');
  },

  async removeFile() {
    return this.request('/remove', {
      method: 'POST',
    });
  },

  async downloadSummary() {
    const response = await fetch(`${API_BASE_URL}/api/download-summary`, {  // Fixed: Added /api prefix
      method: 'POST',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error('Download failed');
    }
    
    return response.blob();
  }
};