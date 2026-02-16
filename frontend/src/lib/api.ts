import axios from 'axios';
import { getToken } from './auth';

const getApiBaseUrl = () => {
    const rawUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    // Remove trailing slash if present
    const cleanUrl = rawUrl.replace(/\/$/, '');
    // Append /api/v1 if not already present
    return cleanUrl.includes('/api/v1') ? cleanUrl : `${cleanUrl}/api/v1`;
};

const API_BASE_URL = getApiBaseUrl();

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Handle unauthorized access (e.g., redirect to login)
            // window.location.href = '/login'; // distinct from router push
            console.error('Unauthorized access');
        }
        return Promise.reject(error);
    }
);
