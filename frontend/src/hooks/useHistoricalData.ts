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
            const candles = response.data.map((c: any) => {
                const dateObj = new Date(c.timestamp);
                // For daily, use string 'yyyy-mm-dd'. For everything else, use unix timestamp (seconds).
                const time = resolution === '1d' 
                    ? c.timestamp.split('T')[0] 
                    :  Math.floor(dateObj.getTime() / 1000); 

                return {
                    time: time,
                    open: c.open,
                    high: c.high,
                    low: c.low,
                    close: c.close,
                    volume: c.volume,
                };
            });

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
