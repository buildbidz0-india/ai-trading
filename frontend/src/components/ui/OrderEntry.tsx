"use client";

import * as React from "react";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function OrderEntry() {
    const { selectedTicker, addOrder, watchlist } = useStore();
    const [side, setSide] = React.useState<"BUY" | "SELL">("BUY");
    const [quantity, setQuantity] = React.useState(50);

    const currentTicker = watchlist.find(t => t.symbol === selectedTicker);
    const currentPrice = currentTicker?.price || 0;

    const handleExecute = () => {
        addOrder({
            id: Math.random().toString(36).substring(7),
            symbol: selectedTicker,
            side,
            type: "MARKET",
            quantity,
            price: currentPrice,
            status: "FILLED",
            timestamp: Date.now(),
        });
        // Visual feedback could go here (toast)
        console.log("Order Executed:", { side, quantity, symbol: selectedTicker });
    };

    return (
        <AcrylicCard variant="solid" className="p-4 space-y-4">
            <div className="font-semibold border-b pb-2 border-border flex justify-between items-center">
                <span>Quick Trade</span>
                <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-muted-foreground">{selectedTicker}</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
                <Button
                    variant={side === "BUY" ? "default" : "outline"}
                    className={cn(
                        "border-green-500/50 hover:bg-green-500/10 text-green-500",
                        side === "BUY" && "bg-green-500/20 hover:bg-green-500/30 text-green-400"
                    )}
                    onClick={() => setSide("BUY")}
                >
                    CALL (Buy)
                </Button>
                <Button
                    variant={side === "SELL" ? "default" : "outline"}
                    className={cn(
                        "border-red-500/50 hover:bg-red-500/10 text-red-500",
                        side === "SELL" && "bg-red-500/20 hover:bg-red-500/30 text-red-400"
                    )}
                    onClick={() => setSide("SELL")}
                >
                    PUT (Buy)
                </Button>
            </div>

            <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                    <label>Quantity</label>
                    <span>Est. Value: ₹{(currentPrice * quantity).toLocaleString()}</span>
                </div>
                <Input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(Number(e.target.value))}
                    className="fluent-input font-mono"
                />
            </div>

            <Button
                onClick={handleExecute}
                className={cn(
                    "w-full shadow-lg transition-all active:scale-95",
                    side === "BUY"
                        ? "bg-green-600 hover:bg-green-500 text-white shadow-green-500/20"
                        : "bg-red-600 hover:bg-red-500 text-white shadow-red-500/20"
                )}
            >
                Execute {side} Order
            </Button>
        </AcrylicCard>
    );
}
