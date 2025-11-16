/**
 * API Client cho RESTful API
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor để thêm token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor để xử lý lỗi
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log lỗi để debug
    if (error.response) {
      // Server trả về response nhưng có status code lỗi
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request được gửi nhưng không nhận được response
      console.error('Network Error:', error.message);
      console.error('Request URL:', error.config?.url);
    } else {
      // Lỗi khi setup request
      console.error('Request Error:', error.message);
    }
    
    if (error.response?.status === 401) {
      // Token hết hạn hoặc không hợp lệ
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (username, email, password) => {
    try {
      console.log('Registering user:', username, email);
      const response = await api.post('/api/auth/register', {
        username,
        email,
        password,
      });
      console.log('Register response:', response.data);
      if (response.data.success && response.data.token) {
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      return response.data;
    } catch (error) {
      console.error('Register error:', error);
      // Trả về error message từ server hoặc message mặc định
      if (error.response?.data) {
        return error.response.data;
      }
      throw error;
    }
  },

  login: async (email, password) => {
    try {
      console.log('Logging in user:', email);
      const response = await api.post('/api/auth/login', {
        email,
        password,
      });
      console.log('Login response:', response.data);
      if (response.data.success && response.data.token) {
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      // Trả về error message từ server hoặc message mặc định
      if (error.response?.data) {
        return error.response.data;
      }
      throw error;
    }
  },

  logout: async () => {
    await api.post('/api/auth/logout');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getCurrentUser: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },
};

// Chat API
export const chatAPI = {
  getMessages: async (receiver = null, limit = 50, offset = 0) => {
    const params = { limit, offset };
    if (receiver) params.receiver = receiver;
    const response = await api.get('/api/chat/messages', { params });
    return response.data;
  },

  sendMessage: async (message, receiver = null) => {
    const response = await api.post('/api/chat/send', {
      message,
      receiver,
    });
    return response.data;
  },

  getConversations: async () => {
    const response = await api.get('/api/chat/conversations');
    return response.data;
  },
};

// User API
export const userAPI = {
  searchUsers: async (query) => {
    const response = await api.get('/api/users/search', {
      params: { q: query },
    });
    return response.data;
  },

  getOnlineUsers: async () => {
    const response = await api.get('/api/users/online');
    return response.data;
  },

  getUserInfo: async (username) => {
    const response = await api.get(`/api/users/${username}`);
    return response.data;
  },
};

// File API
export const fileAPI = {
  uploadFile: async (file, receiver = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (receiver) formData.append('receiver', receiver);
    
    const response = await api.post('/api/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  downloadFile: async (fileId) => {
    const response = await api.get(`/api/files/${fileId}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export default api;

