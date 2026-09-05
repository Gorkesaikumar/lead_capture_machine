import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000, // 30 second timeout — triggers ECONNABORTED on hung requests
  headers: {
    'Content-Type': 'application/json',
    ...(import.meta.env.DEV && { 'ngrok-skip-browser-warning': 'true' }),
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  const orgId = localStorage.getItem('organizationId');
  if (token && config.headers) {
    config.headers.Authorization = `Token ${token}`;
  }
  if (orgId && config.headers) {
    config.headers['X-Organization-ID'] = orgId;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      // Network-level failure: offline, DNS, CORS, or timeout (ECONNABORTED)
      if (import.meta.env.DEV) {
        console.warn('[apiClient] Network error:', error.code, error.message);
      }
    } else if (error.response.status === 401) {
      const url = error.config?.url || '';
      const isLoginRequest = url.includes('/auth/login/');
      const isAlreadyOnLoginPage = window.location.pathname === '/login';

      if (!isLoginRequest && !isAlreadyOnLoginPage) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
