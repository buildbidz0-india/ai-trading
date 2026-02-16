const TOKEN_KEY = 'trading_ai_token';
const REFRESH_TOKEN_KEY = 'trading_ai_refresh_token';

export const setToken = (token: string) => {
    if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, token);
    }
};

export const getToken = (): string | null => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem(TOKEN_KEY);
    }
    return null;
};

export const removeToken = () => {
    if (typeof window !== 'undefined') {
        localStorage.removeItem(TOKEN_KEY);
    }
};

export const setRefreshToken = (token: string) => {
    if (typeof window !== 'undefined') {
        localStorage.setItem(REFRESH_TOKEN_KEY, token);
    }
};

export const getRefreshToken = (): string | null => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    }
    return null;
};

export const removeRefreshToken = () => {
    if (typeof window !== 'undefined') {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
};

export const logout = () => {
    removeToken();
    removeRefreshToken();
    if (typeof window !== 'undefined') {
        window.location.href = '/login';
    }
}
