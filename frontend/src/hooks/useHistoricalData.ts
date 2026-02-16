import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

export type Resolution = '1m' | '3m' | '5m' | '15m' | '30m' | '1h' | '1d';

export interface Candle {
    time: string; // yyyy-mm-dd
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
}

interface UseHistoricalDataReturn {
    data: Candle[];
    loading: boolean;
    error: string | null;
    resolution: Resolution;
    setResolution: (res: Resolution) => void;
    refetch: () => Promise<void>;
}

export function useHistoricalData(symbol: string): UseHistoricalDataReturn {
    const [data, setData] = useState<Candle[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [resolution, setResolution] = useState<Resolution>('1h');

    const fetchData = useCallback(async () => {
        if (!symbol) return;

        setLoading(true);
        setError(null);

        try {
            // Calculate date range based on resolution
            const toDate = new Date();
            const fromDate = new Date();

            // Simple logic: fetch last 30 days for intraday, 1 year for daily
            if (resolution === '1d') {
                fromDate.setFullYear(fromDate.getFullYear() - 1);
            } else if (resolution === '1h') {
                fromDate.setMonth(fromDate.getMonth() - 1);
            } else {
                fromDate.setDate(fromDate.getDate() - 5); // Last 5 days for minute data
            }

            const response = await api.get('/market/history', {
                params: {
                    symbol,
                    resolution,
                    from_date: fromDate.toISOString(),
                    to_date: toDate.toISOString(),
                }
            });

            // Map response to Lightweight Charts format
            // API returns { timestamp: iso_string, ... }
            // Lightweight charts wants 'yyyy-mm-dd' string for daily, or unix timestamp for intraday.
            // For simplicity in this DTO we use string but we might need to cast in the component.
            const candles = response.data.map((c: any) => ({
                time: c.timestamp.split('T')[0], // Quick hack for daily, Component will handle intraday casting
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
                volume: c.volume,
                originalTimestamp: c.timestamp // Keep original for intraday casting
            }));

            setData(candles);
        } catch (err: any) {
            console.error('Failed to fetch historical data:', err);
            setError(err.message || 'Failed to load data');
        } finally {
            setLoading(false);
        }
    }, [symbol, resolution]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    return {
        data,
        loading,
        error,
        resolution,
        setResolution,
        refetch: fetchData
    };
}
