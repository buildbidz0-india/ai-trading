"use client";

import { useState } from "react";
import { AcrylicCard } from "./AcrylicCard";
import { Button } from "./button";
import { Input } from "./input";
import { useStore } from "@/lib/store";

export function OrderEntry() {
    const selectedTicker = useStore((s) => s.selectedTicker);
    const watchlist = useStore((s) => s.watchlist);
    const placeOrder = useStore((s) => s.placeOrder);
    const isPlacingOrder = useStore((s) => s.isPlacingOrder);
    const addOrder = useStore((s) => s.addOrder);

    const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
    const [quantity, setQuantity] = useState(50);
    const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
    const [limitPrice, setLimitPrice] = useState('');
    const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    const ticker = watchlist.find(t => t.symbol === selectedTicker);
    const currentPrice = ticker?.price || 0;

    const handleExecute = async () => {
        setStatus(null);

        try {
            // Try the real API first
            await placeOrder({
                symbol: selectedTicker,
                exchange: 'NSE',
                side: side,
                order_type: orderType,
                product_type: 'INTRADAY',
                quantity: quantity,
                price: orderType === 'LIMIT' ? parseFloat(limitPrice) : currentPrice,
                trigger_price: 0,
                source: 'web_ui',
            });

            setStatus({ type: 'success', message: `${side} order placed for ${quantity} ${selectedTicker}` });
        } catch (err: any) {
            // If the backend is not running, fall back to mock
            console.warn('API call failed, using mock order:', err.message);

            const mockOrder = {
                id: `ORD-${Date.now()}`,
                symbol: selectedTicker,
                side,
                type: orderType,
                quantity,
                price: orderType === 'LIMIT' ? parseFloat(limitPrice) : currentPrice,
                status: 'FILLED' as const,
                timestamp: Date.now(),
            };
            addOrder(mockOrder);
            setStatus({ type: 'success', message: `${side} order placed (mock) for ${quantity} ${selectedTicker}` });
        }
    };

    return (
        <AcrylicCard className="p-4">
            <h3 className="font-semibold text-sm mb-3 text-muted-foreground uppercase tracking-wider">Order Entry</h3>

            {/* Ticker Info */}
            <div className="mb-3 flex justify-between items-baseline">
                <span className="font-bold text-lg">{selectedTicker}</span>
                <span className="text-sm font-mono text-muted-foreground">₹{currentPrice.toLocaleString('en-IN')}</span>
            </div>

            {/* Buy/Sell Toggle */}
            <div className="grid grid-cols-2 gap-2 mb-3">
                <Button
                    variant={side === 'BUY' ? 'default' : 'ghost'}
                    className={side === 'BUY' ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
                    onClick={() => setSide('BUY')}
                >
                    Buy
                </Button>
                <Button
                    variant={side === 'SELL' ? 'default' : 'ghost'}
                    className={side === 'SELL' ? 'bg-red-600 hover:bg-red-700 text-white' : ''}
                    onClick={() => setSide('SELL')}
                >
                    Sell
                </Button>
            </div>

            {/* Order Type */}
            <div className="grid grid-cols-2 gap-2 mb-3">
                <Button
                    variant={orderType === 'MARKET' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setOrderType('MARKET')}
                >
                    Market
                </Button>
                <Button
                    variant={orderType === 'LIMIT' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setOrderType('LIMIT')}
                >
                    Limit
                </Button>
            </div>

            {/* Quantity */}
            <div className="mb-3">
                <label className="text-xs text-muted-foreground block mb-1">Quantity</label>
                <Input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                    className="fluent-input"
                />
            </div>

            {/* Limit Price (conditional) */}
            {orderType === 'LIMIT' && (
                <div className="mb-3">
                    <label className="text-xs text-muted-foreground block mb-1">Limit Price</label>
                    <Input
                        type="number"
                        value={limitPrice}
                        onChange={(e) => setLimitPrice(e.target.value)}
                        placeholder={currentPrice.toString()}
                        className="fluent-input"
                    />
                </div>
            )}

            {/* Order Summary */}
            <div className="text-xs text-muted-foreground mb-3 p-2 rounded bg-muted/50">
                <div className="flex justify-between">
                    <span>Est. Value</span>
                    <span className="font-mono">₹{(currentPrice * quantity).toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between mt-1">
                    <span>Margin Req.</span>
                    <span className="font-mono">₹{((currentPrice * quantity) * 0.2).toLocaleString('en-IN')}</span>
                </div>
            </div>

            {/* Status */}
            {status && (
                <div className={`text-xs mb-2 p-2 rounded ${status.type === 'success' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                    {status.message}
                </div>
            )}

            {/* Execute Button */}
            <Button
                className={`w-full ${side === 'BUY' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'} text-white`}
                onClick={handleExecute}
                disabled={isPlacingOrder}
            >
                {isPlacingOrder ? 'Placing...' : `${side} ${selectedTicker}`}
            </Button>
        </AcrylicCard>
    );
}
