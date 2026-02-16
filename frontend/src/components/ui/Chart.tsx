"use client"
import * as React from "react"
import { createChart, ColorType, IChartApi } from "lightweight-charts"
import { AcrylicCard } from "@/components/ui/AcrylicCard"
import { useStore } from "@/lib/store"

export function ChartComponent() {
    const chartContainerRef = React.useRef<HTMLDivElement>(null)
    const chartRef = React.useRef<IChartApi | null>(null)

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

        // Mock Data
        const data = [
            { time: '2023-12-19', open: 21400, high: 21500, low: 21350, close: 21450 },
            { time: '2023-12-20', open: 21450, high: 21600, low: 21400, close: 21550 },
            { time: '2023-12-21', open: 21550, high: 21650, low: 21500, close: 21100 },
            { time: '2023-12-22', open: 21100, high: 21300, low: 21050, close: 21250 },
            { time: '2023-12-23', open: 21250, high: 21400, low: 21200, close: 21340 },
            { time: '2023-12-24', open: 21340, high: 21450, low: 21300, close: 21400 },
            { time: '2023-12-25', open: 21400, high: 21500, low: 21380, close: 21420 },
        ]

        candlestickSeries.setData(data)
        chart.timeScale().fitContent()

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

    const { selectedTicker } = useStore()

    // ... (rest of useEffect)

    return (
        <AcrylicCard variant="default" className="p-1 h-[450px]">
            <div className="p-3 border-b border-white/5 flex justify-between items-center">
                <div className="text-sm font-medium">{selectedTicker} Index</div>
                <div className="text-xs text-muted-foreground">15m</div>
            </div>
            <div ref={chartContainerRef} className="w-full h-[400px]" />
        </AcrylicCard>
    )
}
