import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Ticker, Order, Position, MarketState, OrderResponse, PositionResponse } from './types';
import { api } from './api';

interface Settings {
    defaultQuantity: number;
    theme: 'dark' | 'light';
    reduceMotion: boolean;
    apiKey?: string;
    secretKey?: string;
}

interface AppState {
    // Market Data
    selectedTicker: string;
    watchlist: Ticker[];
    marketState: MarketState;

    // Trading
    positions: Position[];
    orders: Order[];

    // User Settings
    settings: Settings;

    // Loading states
    isLoadingOrders: boolean;
    isLoadingPositions: boolean;
    isPlacingOrder: boolean;

    // Actions
    setSelectedTicker: (ticker: string) => void;
    updateTicker: (ticker: Ticker) => void;
    addOrder: (order: Order) => void;
    updateMarketStatus: (status: Partial<MarketState>) => void;
    updateSettings: (settings: Partial<Settings>) => void;

    // API Actions
    fetchOrders: () => Promise<void>;
    fetchPositions: () => Promise<void>;
    placeOrder: (order: {
        symbol: string;
        exchange: string;
        side: string;
        order_type: string;
        product_type: string;
        quantity: number;
        price: number;
        trigger_price: number;
        source: string;
    }) => Promise<OrderResponse>;
}

// Mock watchlist data (market data will come from WebSocket)
const INITIAL_WATCHLIST: Ticker[] = [
    { symbol: 'NIFTY', price: 22150.50, change: 120.50, changePercent: 0.55, volume: 1000000, high: 22200, low: 22100 },
    { symbol: 'BANKNIFTY', price: 46500.25, change: -150.00, changePercent: -0.32, volume: 500000, high: 46800, low: 46400 },
    { symbol: 'RELIANCE', price: 2950.00, change: 15.00, changePercent: 0.51, volume: 200000, high: 2960, low: 2940 },
    { symbol: 'HDFCBANK', price: 1420.00, change: -10.00, changePercent: -0.70, volume: 300000, high: 1435, low: 1415 },
    { symbol: 'INFY', price: 1650.00, change: 8.00, changePercent: 0.49, volume: 150000, high: 1660, low: 1640 },
];

export const useStore = create<AppState>()(
    persist(
        (set, get) => ({
            selectedTicker: 'NIFTY',
            watchlist: INITIAL_WATCHLIST,
            marketState: {
                isConnected: false,
                latency: 0,
                lastUpdate: Date.now(),
            },
            positions: [],
            orders: [],
            settings: {
                defaultQuantity: 50,
                theme: 'dark',
                reduceMotion: false,
            },
            isLoadingOrders: false,
            isLoadingPositions: false,
            isPlacingOrder: false,

            setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

            updateTicker: (updatedTicker) => set((state) => ({
                watchlist: state.watchlist.map((t) =>
                    t.symbol === updatedTicker.symbol ? updatedTicker : t
                )
            })),

            addOrder: (order) => set((state) => ({
                orders: [order, ...state.orders]
            })),

            updateMarketStatus: (status) => set((state) => ({
                marketState: { ...state.marketState, ...status }
            })),

            updateSettings: (newSettings) => set((state) => ({
                settings: { ...state.settings, ...newSettings }
            })),

            // ── API Actions ─────────────────────
            fetchOrders: async () => {
                set({ isLoadingOrders: true });
                try {
                    const { data } = await api.get<OrderResponse[]>('/orders');
                    const orders: Order[] = data.map((o) => ({
                        id: o.id,
                        symbol: o.symbol,
                        side: o.side as 'BUY' | 'SELL',
                        type: o.order_type as 'MARKET' | 'LIMIT',
                        quantity: o.quantity,
                        price: parseFloat(o.price),
                        status: o.status as Order['status'],
                        timestamp: new Date(o.created_at).getTime(),
                        exchange: o.exchange,
                        order_type: o.order_type,
                        product_type: o.product_type,
                        broker_order_id: o.broker_order_id ?? undefined,
                        rejection_reason: o.rejection_reason ?? undefined,
                        source: o.source,
                    }));
                    set({ orders, isLoadingOrders: false });
                } catch (err) {
                    console.error('Failed to fetch orders:', err);
                    set({ isLoadingOrders: false });
                }
            },

            fetchPositions: async () => {
                set({ isLoadingPositions: true });
                try {
                    const { data } = await api.get<PositionResponse[]>('/positions');
                    const positions: Position[] = data.map((p) => ({
                        id: p.id,
                        symbol: p.symbol,
                        quantity: p.net_quantity,
                        averagePrice: parseFloat(p.average_price),
                        currentPrice: 0, // Will be updated by WebSocket ticks
                        pnl: parseFloat(p.unrealised_pnl),
                        pnlPercent: 0,
                        instrument_id: p.instrument_id,
                        exchange: p.exchange,
                        net_quantity: p.net_quantity,
                        realised_pnl: p.realised_pnl,
                        unrealised_pnl: p.unrealised_pnl,
                        greeks: p.greeks,
                    }));
                    set({ positions, isLoadingPositions: false });
                } catch (err) {
                    console.error('Failed to fetch positions:', err);
                    set({ isLoadingPositions: false });
                }
            },

            placeOrder: async (orderReq) => {
                set({ isPlacingOrder: true });
                try {
                    const { data } = await api.post<OrderResponse>('/orders', orderReq);

                    // Add to local state immediately
                    const order: Order = {
                        id: data.id,
                        symbol: data.symbol,
                        side: data.side as 'BUY' | 'SELL',
                        type: data.order_type as 'MARKET' | 'LIMIT',
                        quantity: data.quantity,
                        price: parseFloat(data.price),
                        status: data.status as Order['status'],
                        timestamp: new Date(data.created_at).getTime(),
                        exchange: data.exchange,
                        source: data.source,
                    };
                    set((state) => ({
                        orders: [order, ...state.orders],
                        isPlacingOrder: false,
                    }));
                    return data;
                } catch (err) {
                    set({ isPlacingOrder: false });
                    throw err;
                }
            },
        }),
        {
            name: 'trading-ai-storage', // unique name
            partialize: (state) => ({ settings: state.settings }), // only persist settings
        }
    )
);
