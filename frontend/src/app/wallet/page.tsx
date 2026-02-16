"use client";

import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export default function WalletPage() {
    const { positions, orders } = useStore();

    return (
        <Shell>
            <div className="space-y-6">
                <h1 className="text-2xl font-bold">Wallet & Positions</h1>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <AcrylicCard className="p-6 space-y-2">
                        <div className="text-sm text-muted-foreground">Total P&L</div>
                        <div className="text-3xl font-bold text-green-500">+₹12,450.00</div>
                    </AcrylicCard>
                    <AcrylicCard className="p-6 space-y-2">
                        <div className="text-sm text-muted-foreground">Available Margin</div>
                        <div className="text-3xl font-bold">₹1,45,000.00</div>
                    </AcrylicCard>
                    <AcrylicCard className="p-6 space-y-2">
                        <div className="text-sm text-muted-foreground">Used Margin</div>
                        <div className="text-3xl font-bold">₹55,000.00</div>
                    </AcrylicCard>
                </div>

                <AcrylicCard className="flex flex-col overflow-hidden">
                    <div className="p-4 border-b border-border bg-muted/20">
                        <h3 className="font-semibold">Open Positions</h3>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-muted/10 text-xs text-muted-foreground text-left">
                                <tr>
                                    <th className="p-4 font-medium">Symbol</th>
                                    <th className="p-4 font-medium text-right">Qty</th>
                                    <th className="p-4 font-medium text-right">Avg. Price</th>
                                    <th className="p-4 font-medium text-right">LTP</th>
                                    <th className="p-4 font-medium text-right">P&L</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="p-8 text-center text-muted-foreground">No open positions</td>
                                    </tr>
                                ) : (
                                    positions.map((pos) => (
                                        <tr key={pos.symbol} className="border-b border-border/50 hover:bg-muted/50">
                                            <td className="p-4 font-medium">{pos.symbol}</td>
                                            <td className="p-4 text-right">{pos.quantity}</td>
                                            <td className="p-4 text-right">{pos.averagePrice}</td>
                                            <td className="p-4 text-right">{pos.currentPrice}</td>
                                            <td className={cn("p-4 text-right font-bold", pos.pnl >= 0 ? "text-green-500" : "text-red-500")}>
                                                {pos.pnl > 0 ? "+" : ""}{pos.pnl}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </AcrylicCard>

                <AcrylicCard className="flex flex-col overflow-hidden">
                    <div className="p-4 border-b border-border bg-muted/20">
                        <h3 className="font-semibold">Order History</h3>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-muted/10 text-xs text-muted-foreground text-left">
                                <tr>
                                    <th className="p-4 font-medium">Time</th>
                                    <th className="p-4 font-medium">Symbol</th>
                                    <th className="p-4 font-medium">Type</th>
                                    <th className="p-4 font-medium text-right">Qty</th>
                                    <th className="p-4 font-medium text-right">Price</th>
                                    <th className="p-4 font-medium text-right">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="p-8 text-center text-muted-foreground">No orders yet</td>
                                    </tr>
                                ) : (
                                    orders.map((order) => (
                                        <tr key={order.id} className="border-b border-border/50 hover:bg-muted/50">
                                            <td className="p-4 text-muted-foreground">{new Date(order.timestamp).toLocaleTimeString()}</td>
                                            <td className="p-4 font-medium">{order.symbol}</td>
                                            <td className={cn("p-4 font-medium", order.side === "BUY" ? "text-green-500" : "text-red-500")}>
                                                {order.side}
                                            </td>
                                            <td className="p-4 text-right">{order.quantity}</td>
                                            <td className="p-4 text-right">{order.price}</td>
                                            <td className="p-4 text-right">
                                                <span className="bg-muted px-2 py-1 rounded text-xs">{order.status}</span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </AcrylicCard>
            </div>
        </Shell>
    );
}
