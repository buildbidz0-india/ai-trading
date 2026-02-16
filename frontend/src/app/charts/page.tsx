"use client";

import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { ChartComponent } from "@/components/ui/Chart";

export default function ChartsPage() {
    return (
        <Shell>
            <div className="flex flex-col h-[calc(100vh-8rem)]">
                <h1 className="text-2xl font-bold mb-4">Market Analysis</h1>
                <div className="flex-1">
                    <ChartComponent />
                </div>
            </div>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                <AcrylicCard className="p-4">
                    <h3 className="font-semibold text-sm mb-2">Technicals</h3>
                    <div className="text-muted-foreground text-sm">RSI: 64.5 (Neutral)</div>
                    <div className="text-muted-foreground text-sm">MACD: Bullish Crossover</div>
                </AcrylicCard>
                <AcrylicCard className="p-4">
                    <h3 className="font-semibold text-sm mb-2">Market Depth</h3>
                    <div className="text-green-500 text-sm">Bid: 22,148.00 (500)</div>
                    <div className="text-red-500 text-sm">Ask: 22,149.50 (350)</div>
                </AcrylicCard>
                <AcrylicCard className="p-4">
                    <h3 className="font-semibold text-sm mb-2">Price Stats</h3>
                    <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">High</span>
                        <span>22,200.00</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Low</span>
                        <span>22,100.00</span>
                    </div>
                </AcrylicCard>
            </div>
        </Shell>
    );
}
