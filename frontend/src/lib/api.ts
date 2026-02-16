import axios from 'axios';
import { getToken } from './auth';

const getApiBaseUrl = () => {
    // In production, we can often use relative paths if on the same domain
    if (typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_API_URL) {
        return '/api/v1/';
    }

    const rawUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    // Remove trailing slash if present, then add exactly one
    const cleanUrl = rawUrl.replace(/\/$/, '');

    // If it doesn't already have the version, add it
    const versionedUrl = cleanUrl.includes('/api/v1') ? cleanUrl : `${cleanUrl}/api/v1`;

    // Ensure it ends with a slash for predictable merging
    const finalUrl = `${versionedUrl}/`;
    console.log('API Base URL:', finalUrl);
    return finalUrl;
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
