import axios from 'axios';
import { getStoredAdminKey } from '../utils/auth';

const apiClient = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api`,
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
