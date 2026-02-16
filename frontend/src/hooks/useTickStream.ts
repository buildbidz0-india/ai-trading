"use client";

import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '@/lib/store';
import { getToken } from '@/lib/auth';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000';
const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

/**
 * Hook that manages a WebSocket connection to the live tick stream.
 * Automatically reconnects on disconnect and updates the store with live data.
 */
export function useTickStream() {
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttempts = useRef(0);
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

    const updateTicker = useStore((s) => s.updateTicker);
    const updateMarketStatus = useStore((s) => s.updateMarketStatus);

    const connect = useCallback(() => {
        const token = getToken();
        if (!token) {
            console.warn('[useTickStream] No token — skipping WS connection');
            return;
        }

        // Don't create duplicate connections
        if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
            return;
        }

        const url = `${WS_BASE_URL}/ws/v1/ticks?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[WS] Tick stream connected');
            reconnectAttempts.current = 0;
            updateMarketStatus({ isConnected: true, lastUpdate: Date.now() });
        };

        ws.onmessage = (event) => {
            const start = performance.now();
            try {
                const data = JSON.parse(event.data);

                // Map backend tick data to our Ticker interface
                if (data.symbol) {
                    updateTicker({
                        symbol: data.symbol,
                        price: data.ltp ?? data.last_price ?? data.price ?? 0,
                        change: data.change ?? 0,
                        changePercent: data.change_pct ?? data.change_percent ?? 0,
                        volume: data.volume ?? 0,
                        high: data.high ?? 0,
                        low: data.low ?? 0,
                    });
                }

                const latency = Math.round(performance.now() - start);
                updateMarketStatus({ latency, lastUpdate: Date.now() });
            } catch (err) {
                console.error('[WS] Failed to parse tick:', err);
            }
        };

        ws.onerror = (err) => {
            console.error('[WS] Connection error:', err);
        };

        ws.onclose = (event) => {
            console.log('[WS] Disconnected:', event.code, event.reason);
            updateMarketStatus({ isConnected: false });

            // Auto-reconnect with backoff
            if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
                const delay = RECONNECT_DELAY_MS * Math.pow(1.5, reconnectAttempts.current);
                console.log(`[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${reconnectAttempts.current + 1})`);
                reconnectTimer.current = setTimeout(() => {
                    reconnectAttempts.current++;
                    connect();
                }, delay);
            } else {
                console.warn('[WS] Max reconnect attempts reached');
            }
        };
    }, [updateTicker, updateMarketStatus]);

    const disconnect = useCallback(() => {
        if (reconnectTimer.current) {
            clearTimeout(reconnectTimer.current);
            reconnectTimer.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        updateMarketStatus({ isConnected: false });
    }, [updateMarketStatus]);

    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return {
        isConnected: wsRef.current?.readyState === WebSocket.OPEN,
        reconnect: connect,
        disconnect,
    };
}
