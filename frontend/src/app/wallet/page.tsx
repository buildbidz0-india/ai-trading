"use client";

import { useEffect } from "react";
import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { useStore } from "@/lib/store";

export default function WalletPage() {
    const positions = useStore((s) => s.positions);
    const orders = useStore((s) => s.orders);
    const fetchPositions = useStore((s) => s.fetchPositions);
    const fetchOrders = useStore((s) => s.fetchOrders);
    const isLoadingPositions = useStore((s) => s.isLoadingPositions);
    const isLoadingOrders = useStore((s) => s.isLoadingOrders);

    useEffect(() => {
        fetchPositions();
        fetchOrders();
    }, [fetchPositions, fetchOrders]);

    const totalPnl = positions.reduce((sum, p) => sum + p.pnl, 0);

    return (
        <Shell>
            <h1 className="text-2xl font-bold mb-4">Portfolio</h1>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <AcrylicCard className="p-4">
                    <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Total P&L</div>
                    <div className={`text-2xl font-bold font-mono ${totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {totalPnl >= 0 ? '+' : ''}₹{totalPnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                </AcrylicCard>
                <AcrylicCard className="p-4">
                    <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Open Positions</div>
                    <div className="text-2xl font-bold font-mono">{positions.length}</div>
                </AcrylicCard>
                <AcrylicCard className="p-4">
                    <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Orders Today</div>
                    <div className="text-2xl font-bold font-mono">{orders.length}</div>
                </AcrylicCard>
            </div>

            {/* Positions Table */}
            <AcrylicCard className="p-4 mb-6">
                <h2 className="font-semibold text-sm mb-3 text-muted-foreground uppercase tracking-wider">Open Positions</h2>
                {isLoadingPositions ? (
                    <div className="text-sm text-muted-foreground py-4 text-center">Loading positions...</div>
                ) : positions.length === 0 ? (
                    <div className="text-sm text-muted-foreground py-4 text-center">No open positions</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-xs text-muted-foreground uppercase border-b border-border">
                                    <th className="text-left py-2 px-2">Symbol</th>
                                    <th className="text-right py-2 px-2">Qty</th>
                                    <th className="text-right py-2 px-2">Avg Price</th>
                                    <th className="text-right py-2 px-2">P&L</th>
                                    <th className="text-right py-2 px-2">Greeks</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.map((p, i) => (
                                    <tr key={p.id || i} className="border-b border-border/30 hover:bg-muted/30 transition-colors">
                                        <td className="py-2 px-2 font-medium">{p.symbol}</td>
                                        <td className="py-2 px-2 text-right font-mono">{p.quantity}</td>
                                        <td className="py-2 px-2 text-right font-mono">₹{p.averagePrice.toFixed(2)}</td>
                                        <td className={`py-2 px-2 text-right font-mono ${p.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            {p.pnl >= 0 ? '+' : ''}₹{p.pnl.toFixed(2)}
                                        </td>
                                        <td className="py-2 px-2 text-right text-xs text-muted-foreground">
                                            {p.greeks ? `Δ${p.greeks.delta.toFixed(2)} Θ${p.greeks.theta.toFixed(2)}` : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </AcrylicCard>

            {/* Order History */}
            <AcrylicCard className="p-4">
                <h2 className="font-semibold text-sm mb-3 text-muted-foreground uppercase tracking-wider">Order History</h2>
                {isLoadingOrders ? (
                    <div className="text-sm text-muted-foreground py-4 text-center">Loading orders...</div>
                ) : orders.length === 0 ? (
                    <div className="text-sm text-muted-foreground py-4 text-center">No orders yet</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-xs text-muted-foreground uppercase border-b border-border">
                                    <th className="text-left py-2 px-2">ID</th>
                                    <th className="text-left py-2 px-2">Symbol</th>
                                    <th className="text-left py-2 px-2">Side</th>
                                    <th className="text-right py-2 px-2">Qty</th>
                                    <th className="text-right py-2 px-2">Price</th>
                                    <th className="text-left py-2 px-2">Status</th>
                                    <th className="text-right py-2 px-2">Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.map((o, i) => (
                                    <tr key={o.id || i} className="border-b border-border/30 hover:bg-muted/30 transition-colors">
                                        <td className="py-2 px-2 text-xs font-mono text-muted-foreground">{o.id.slice(0, 8)}</td>
                                        <td className="py-2 px-2 font-medium">{o.symbol}</td>
                                        <td className={`py-2 px-2 font-semibold ${o.side === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                                            {o.side}
                                        </td>
                                        <td className="py-2 px-2 text-right font-mono">{o.quantity}</td>
                                        <td className="py-2 px-2 text-right font-mono">₹{o.price.toFixed(2)}</td>
                                        <td className="py-2 px-2">
                                            <span className={`text-xs px-1.5 py-0.5 rounded ${o.status === 'FILLED' ? 'bg-green-500/10 text-green-500' :
                                                    o.status === 'PENDING' ? 'bg-yellow-500/10 text-yellow-500' :
                                                        o.status === 'CANCELLED' ? 'bg-muted text-muted-foreground' :
                                                            'bg-red-500/10 text-red-500'
                                                }`}>
                                                {o.status}
                                            </span>
                                        </td>
                                        <td className="py-2 px-2 text-right text-xs text-muted-foreground">
                                            {new Date(o.timestamp).toLocaleTimeString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </AcrylicCard>
        </Shell>
    );
}
