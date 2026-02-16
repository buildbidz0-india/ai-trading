import { getToken } from './auth';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000';

type TickData = {
    symbol: string;
    ltp: number;
    change: number;
    change_pct: number;
    volume: number;
    high: number;
    low: number;
    open: number;
    timestamp: string;
};

type WSMessageHandler = (data: TickData) => void;

/**
 * Creates a WebSocket connection to the live tick stream.
 * Requires JWT authentication via query parameter.
 */
export function createTickStream(onMessage: WSMessageHandler, onError?: (err: Event) => void) {
    const token = getToken();
    if (!token) {
        console.warn('[WS] No authentication token available for tick stream');
        return null;
    }

    const url = `${WS_BASE_URL}/ws/v1/ticks?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
        console.log('[WS] Tick stream connected');
    };

    ws.onmessage = (event) => {
        try {
            const data: TickData = JSON.parse(event.data);
            onMessage(data);
        } catch (err) {
            console.error('[WS] Failed to parse tick data:', err);
        }
    };

    ws.onerror = (err) => {
        console.error('[WS] Tick stream error:', err);
        onError?.(err);
    };

    ws.onclose = (event) => {
        console.log('[WS] Tick stream closed:', event.code, event.reason);
    };

    return ws;
}

/**
 * Creates a WebSocket connection for AI agent log streaming.
 */
export function createAgentLogStream(
    onMessage: (data: any) => void,
    onError?: (err: Event) => void
) {
    const token = getToken();
    if (!token) {
        console.warn('[WS] No authentication token for agent log stream');
        return null;
    }

    const url = `${WS_BASE_URL}/ws/v1/agent-log?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
        console.log('[WS] Agent log stream connected');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
        } catch (err) {
            console.error('[WS] Failed to parse agent log:', err);
        }
    };

    ws.onerror = (err) => {
        console.error('[WS] Agent log stream error:', err);
        onError?.(err);
    };

    ws.onclose = (event) => {
        console.log('[WS] Agent log stream closed:', event.code, event.reason);
    };

    return ws;
}
