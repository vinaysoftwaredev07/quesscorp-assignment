import axios from 'axios';
import { getStoredAdminKey } from '../utils/auth';

const defaultApiBaseUrl = (() => {
  if (typeof window === 'undefined') {
    return 'http://localhost:8001';
  }

  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8001`;
})();

const apiClient = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl}/api`,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error?.response?.data?.message || 'Unexpected error occurred';
    return Promise.reject(new Error(message));
  },
);

apiClient.interceptors.request.use((config) => {
  const adminKey = getStoredAdminKey();
  if (adminKey) {
    config.headers['X-Superadmin-Key'] = adminKey;
  }
  return config;
});

export default apiClient;
