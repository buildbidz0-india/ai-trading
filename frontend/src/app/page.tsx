"use client";

import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { ChartComponent } from "@/components/ui/Chart";
import { cn } from "@/lib/utils";
import { Watchlist } from "@/components/ui/Watchlist";
import { OrderEntry } from "@/components/ui/OrderEntry";
import { useTickStream } from "@/hooks/useTickStream";
import { AgentLog } from "@/components/ui/AgentLog";

export default function Home() {
  // Connect to live WebSocket tick stream
  useTickStream();

  return (
    <Shell>
      <div className="grid grid-cols-12 gap-6 h-full">
        {/* Left Column: Chart & Market Data */}
        <div className="col-span-12 lg:col-span-9 flex flex-col gap-6">
          <ChartComponent />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <AcrylicCard className="p-4 space-y-2">
              <div className="text-sm text-muted-foreground">Open Interest (PCR)</div>
              <div className="text-2xl font-semibold">0.85 <span className="text-sm text-red-500 font-normal">Bearish</span></div>
              <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-red-500 w-[45%]" />
              </div>
            </AcrylicCard>

            <AcrylicCard className="p-4 space-y-2">
              <div className="text-sm text-muted-foreground">Max Pain</div>
              <div className="text-2xl font-semibold">22,100</div>
              <div className="text-xs text-muted-foreground">Expiry: 29 Feb</div>
            </AcrylicCard>

            <AcrylicCard className="p-4 space-y-2">
              <div className="text-sm text-muted-foreground">IV Percentile</div>
              <div className="text-2xl font-semibold">45% <span className="text-sm text-yellow-500 font-normal">Moderate</span></div>
            </AcrylicCard>
          </div>
        </div>

        {/* Right Column: Trade Panel & AI Log */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
          <Watchlist />
          <OrderEntry />
          <AgentLog />
        </div>
      </div>
    </Shell>
  );
}
