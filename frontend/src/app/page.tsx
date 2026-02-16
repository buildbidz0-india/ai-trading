"use client";

import { Shell } from "@/components/layout/Shell";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { ChartComponent } from "@/components/ui/Chart";
import { cn } from "@/lib/utils";
import { Watchlist } from "@/components/ui/Watchlist";
import { OrderEntry } from "@/components/ui/OrderEntry";
import { useTickStream } from "@/hooks/useTickStream";

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

          {/* AI Agent Log */}
          <AcrylicCard className="flex-1 flex flex-col p-4 min-h-[300px]">
            <div className="font-semibold mb-3 flex items-center gap-2">
              <div className="size-2 rounded-full bg-green-500 animate-pulse" />
              AI Agent Log
            </div>
            <div className="flex-1 overflow-auto space-y-3 pr-2 text-sm font-mono scrollbar-thin scrollbar-thumb-white/10">
              <LogEntry time="10:30:05" type="INFO" msg="Scanning NIFTY 50 Option Chain..." />
              <LogEntry time="10:30:12" type="ANALYSIS" msg="Detected Bullish divergence in RSI." color="text-blue-400" />
              <LogEntry time="10:30:45" type="DECISION" msg="Holding position. Waiting for confirm." color="text-yellow-400" />
              <LogEntry time="10:31:00" type="INFO" msg="PCR Shifted to 0.87" />
            </div>
          </AcrylicCard>
        </div>
      </div>
    </Shell>
  );
}

function LogEntry({ time, type, msg, color }: { time: string, type: string, msg: string, color?: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-muted-foreground opacity-50 shrink-0">[{time}]</span>
      <span className={cn("break-words", color)}><span className="font-bold opacity-70">{type}:</span> {msg}</span>
    </div>
  )
}
