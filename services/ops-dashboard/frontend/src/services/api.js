import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// API endpoints
export const apiService = {
  // Incidents
  getIncidents: (params = {}) => api.get('/incidents', { params }),
  getIncident: (id) => api.get(`/incidents/${id}`),

  // Agents
  getAgents: () => api.get('/agents'),
  getAgentStatus: (agentName) => api.get(`/agents/${agentName}/status`),

  // Metrics
  getMetrics: (params = {}) => api.get('/metrics', { params }),
  getSystemHealth: () => api.get('/health'),

  // Analytics
  getIncidentStats: (timeRange = '24h') => api.get(`/analytics/incidents?range=${timeRange}`),
  getAgentStats: () => api.get('/analytics/agents'),
};

export default api;
