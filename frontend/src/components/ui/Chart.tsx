"use client"
import * as React from "react"
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts"
import { AcrylicCard } from "@/components/ui/AcrylicCard"
import { useStore } from "@/lib/store"
import { useHistoricalData, Resolution } from "@/hooks/useHistoricalData"
import { cn } from "@/lib/utils"

const TIMEFRAMES: { label: string; value: Resolution }[] = [
    { label: '1M', value: '1m' },
    { label: '5M', value: '5m' },
    { label: '15M', value: '15m' },
    { label: '1H', value: '1h' },
    { label: '1D', value: '1d' },
]

export function ChartComponent() {
    const chartContainerRef = React.useRef<HTMLDivElement>(null)
    const chartRef = React.useRef<IChartApi | null>(null)
    const seriesRef = React.useRef<ISeriesApi<"Candlestick"> | null>(null)

    const { selectedTicker } = useStore()
    const { data, loading, error, resolution, setResolution } = useHistoricalData(selectedTicker || "NIFTY")

    // Initialize Chart
    React.useEffect(() => {
        if (!chartContainerRef.current) return

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#A1A1AA', // zinc-400
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            }
        })

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#22c55e', // green-500
            downColor: '#ef4444', // red-500
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        })

        seriesRef.current = candlestickSeries
        chartRef.current = chart

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth })
            }
        }

        window.addEventListener('resize', handleResize)

        return () => {
            window.removeEventListener('resize', handleResize)
            chart.remove()
        }
    }, [])

    // Update Data
    React.useEffect(() => {
        if (seriesRef.current && data.length > 0) {
            seriesRef.current.setData(data)
            chartRef.current?.timeScale().fitContent()
        }
    }, [data])

    return (
        <AcrylicCard variant="default" className="p-1 h-[450px] relative flex flex-col">
            {/* Header / Controls */}
            <div className="p-3 border-b border-white/5 flex justify-between items-center shrink-0">
                <div className="flex items-center gap-4">
                    <div className="text-sm font-medium">{selectedTicker || "NIFTY"}</div>

                    {/* Timeframe Selector */}
                    <div className="flex bg-muted/20 rounded-lg p-0.5">
                        {TIMEFRAMES.map((tf) => (
                            <button
                                key={tf.value}
                                onClick={() => setResolution(tf.value)}
                                className={cn(
                                    "px-2 py-0.5 text-[10px] font-medium rounded transition-all",
                                    resolution === tf.value
                                        ? "bg-primary/20 text-primary shadow-sm"
                                        : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                )}
                            >
                                {tf.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {loading && (
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground animate-pulse">
                            <div className="size-1.5 bg-primary rounded-full" />
                            Loading...
                        </div>
                    )}
                    {error && (
                        <div className="text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                            Failed to load
                        </div>
                    )}
                </div>
            </div>

            {/* Chart Container */}
            <div className="flex-1 relative w-full min-h-0">
                <div ref={chartContainerRef} className="absolute inset-0" />
            </div>
        </AcrylicCard>
    )
}
