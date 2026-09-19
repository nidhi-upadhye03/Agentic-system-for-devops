import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor - no auth required
api.interceptors.request.use(
  (config) => {
    // No authentication needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't redirect on 401, just log the error
    if (error.response?.status === 401) {
      console.warn('API returned 401, but auth is disabled');
    }
    return Promise.reject(error);
  }
);

// Authentication APIs
export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated: () => {
    const token = localStorage.getItem('token');
    if (!token) return false;

    try {
      const decoded = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      return decoded.exp > currentTime;
    } catch (error) {
      return false;
    }
  },
};

// Helper function to transform snake_case to camelCase
const toCamelCase = (obj) => {
  if (Array.isArray(obj)) {
    return obj.map(item => toCamelCase(item));
  } else if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((result, key) => {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      result[camelKey] = toCamelCase(obj[key]);
      return result;
    }, {});
  }
  return obj;
};

// Approval APIs
export const approvalAPI = {
  // Get all approvals (with optional filters)
  getApprovals: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.type) params.append('type', filters.type);
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.search) params.append('search', filters.search);

    const response = await api.get(`/approvals?${params.toString()}`);
    // Transform snake_case to camelCase
    if (response.data.data) {
      response.data.data = toCamelCase(response.data.data);
    }
    return response.data;
  },

  // Get single approval by ID
  getApprovalById: async (id) => {
    const response = await api.get(`/approvals/${id}`);
    // Transform snake_case to camelCase
    if (response.data.data) {
      response.data.data = toCamelCase(response.data.data);
    }
    return response.data;
  },

  // Create new approval
  createApproval: async (approvalData) => {
    const response = await api.post('/approvals', approvalData);
    return response.data;
  },

  // Update approval
  updateApproval: async (id, approvalData) => {
    const response = await api.put(`/approvals/${id}`, approvalData);
    return response.data;
  },

  // Delete approval
  deleteApproval: async (id) => {
    const response = await api.delete(`/approvals/${id}`);
    return response.data;
  },

  // Approve an approval request
  approve: async (id, comment = '') => {
    const response = await api.post(`/approvals/${id}/approve`, { comment });
    return response.data;
  },

  // Reject an approval request
  reject: async (id, comment = '') => {
    const response = await api.post(`/approvals/${id}/reject`, { comment });
    return response.data;
  },

  // Rollback an approval
  rollback: async (id, comment = '') => {
    const response = await api.post(`/approvals/${id}/rollback`, { comment });
    return response.data;
  },

  // Get approval history
  getHistory: async (id) => {
    const response = await api.get(`/approvals/${id}/history`);
    return response.data;
  },

  // Get approvals pending for current user
  getMyPendingApprovals: async () => {
    const response = await api.get('/approvals/my/pending');
    return response.data;
  },

  // Get approvals created by current user
  getMyApprovals: async () => {
    const response = await api.get('/approvals/my/created');
    return response.data;
  },
};

// Notification APIs
export const notificationAPI = {
  getNotifications: async () => {
    const response = await api.get('/notifications');
    return response.data;
  },

  markAsRead: async (id) => {
    const response = await api.put(`/notifications/${id}/read`);
    return response.data;
  },

  markAllAsRead: async () => {
    const response = await api.put('/notifications/read-all');
    return response.data;
  },

  deleteNotification: async (id) => {
    const response = await api.delete(`/notifications/${id}`);
    return response.data;
  },
};

// User APIs
export const userAPI = {
  getUsers: async () => {
    const response = await api.get('/users');
    return response.data;
  },

  getUserById: async (id) => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },

  updateProfile: async (userData) => {
    const response = await api.put('/users/profile', userData);
    return response.data;
  },
};

// Analytics APIs
export const analyticsAPI = {
  getStats: async () => {
    const response = await api.get('/analytics/stats');
    return response.data;
  },

  getApprovalTrends: async (period = '30d') => {
    const response = await api.get(`/analytics/trends?period=${period}`);
    return response.data;
  },
};

export default api;
