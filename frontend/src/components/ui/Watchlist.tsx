"use client";

import { useStore } from "@/lib/store";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { cn } from "@/lib/utils";

export function Watchlist() {
    const { watchlist, selectedTicker, setSelectedTicker } = useStore();

    return (
        <AcrylicCard className="flex flex-col h-[300px] p-0 overflow-hidden">
            <div className="p-3 border-b border-border bg-muted/20">
                <h3 className="font-semibold text-sm">Market Watch</h3>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-muted">
                <table className="w-full text-sm">
                    <thead className="bg-muted/10 sticky top-0 backdrop-blur-md z-10 text-xs text-muted-foreground">
                        <tr>
                            <th className="text-left p-2 font-medium">Symbol</th>
                            <th className="text-right p-2 font-medium">Price</th>
                            <th className="text-right p-2 font-medium">%</th>
                        </tr>
                    </thead>
                    <tbody>
                        {watchlist.map((ticker) => (
                            <tr
                                key={ticker.symbol}
                                onClick={() => setSelectedTicker(ticker.symbol)}
                                className={cn(
                                    "cursor-pointer transition-colors border-b border-border/50 hover:bg-muted/50",
                                    selectedTicker === ticker.symbol && "bg-primary/10 border-l-2 border-l-primary"
                                )}
                            >
                                <td className="p-2 font-medium">{ticker.symbol}</td>
                                <td className="text-right p-2">{ticker.price.toFixed(2)}</td>
                                <td
                                    className={cn(
                                        "text-right p-2",
                                        ticker.changePercent >= 0 ? "text-green-500" : "text-red-500"
                                    )}
                                >
                                    {ticker.changePercent > 0 ? "+" : ""}
                                    {ticker.changePercent.toFixed(2)}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </AcrylicCard>
    );
}
