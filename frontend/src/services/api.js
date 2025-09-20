import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Create axios instance with common config
const apiClient = axios.create({
  baseURL: API,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Portfolio API calls
export const portfolioAPI = {
  getHero: async () => {
    const response = await apiClient.get('/portfolio/hero');
    return response.data;
  },

  getAbout: async () => {
    const response = await apiClient.get('/portfolio/about');
    return response.data;
  },

  getProjects: async (params = {}) => {
    const response = await apiClient.get('/portfolio/projects', { params });
    return response.data;
  },

  getExperience: async () => {
    const response = await apiClient.get('/portfolio/experience');
    return response.data;
  },

  getSkills: async () => {
    const response = await apiClient.get('/portfolio/skills');
    return response.data;
  },

  getCertifications: async () => {
    const response = await apiClient.get('/portfolio/certifications');
    return response.data;
  },

  getContact: async () => {
    const response = await apiClient.get('/portfolio/contact');
    return response.data;
  }
};

// Contact API calls
export const contactAPI = {
  submitMessage: async (messageData) => {
    const response = await apiClient.post('/contact/message', messageData);
    return response.data;
  },

  getContactInfo: async () => {
    const response = await apiClient.get('/contact/info');
    return response.data;
  }
};

// Error handling wrapper
export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    console.error('API Error:', error.response.data);
    return error.response.data.detail || 'An error occurred';
  } else if (error.request) {
    // Network error
    console.error('Network Error:', error.request);
    return 'Network error. Please check your connection.';
  } else {
    // Other error
    console.error('Error:', error.message);
    return error.message;
  }
};

export default apiClient;