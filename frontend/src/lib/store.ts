import { create } from 'zustand';
import { Ticker, Order, Position, MarketState } from './types';

interface AppState {
    // Market Data
    selectedTicker: string;
    watchlist: Ticker[];
    marketState: MarketState;

    // Trading
    positions: Position[];
    orders: Order[];

    // Actions
    setSelectedTicker: (ticker: string) => void;
    updateTicker: (ticker: Ticker) => void;
    addOrder: (order: Order) => void;
    updateMarketStatus: (status: Partial<MarketState>) => void;
}

// Mock Initial Data
const INITIAL_WATCHLIST: Ticker[] = [
    { symbol: 'NIFTY', price: 22150.50, change: 120.50, changePercent: 0.55, volume: 1000000, high: 22200, low: 22100 },
    { symbol: 'BANKNIFTY', price: 46500.25, change: -150.00, changePercent: -0.32, volume: 500000, high: 46800, low: 46400 },
    { symbol: 'RELIANCE', price: 2950.00, change: 15.00, changePercent: 0.51, volume: 200000, high: 2960, low: 2940 },
    { symbol: 'HDFCBANK', price: 1420.00, change: -10.00, changePercent: -0.70, volume: 300000, high: 1435, low: 1415 },
    { symbol: 'INFY', price: 1650.00, change: 8.00, changePercent: 0.49, volume: 150000, high: 1660, low: 1640 },
];

export const useStore = create<AppState>((set) => ({
    selectedTicker: 'NIFTY',
    watchlist: INITIAL_WATCHLIST,
    marketState: {
        isConnected: false,
        latency: 0,
        lastUpdate: Date.now(),
    },
    positions: [],
    orders: [],

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
    }))
}));
