'use client'
import { ColorType, IChartApi, ISeriesApi } from 'lightweight-charts'
import { useEffect, useRef, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface PriceChartProps {
    symbol: string
    isDark?: boolean
}

export default function PriceChart({ symbol, isDark = true }: PriceChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null)
    const [chartData, setChartData] = useState<{ time: number; value: number }[]>([])
    const chartRef = useRef<IChartApi | null>(null)
    const seriesRef = useRef<ISeriesApi<"Area"> | null>(null)

    // 1. Fetch Initial Data
    useEffect(() => {
        const fetchData = async () => {
            const { data } = await supabase
                .from('market_data')
                .select('timestamp, price')
                .eq('symbol', symbol)
                .order('timestamp', { ascending: true })
                .limit(2000)

            if (data) {
                const formatted = data.map(d => ({
                    time: new Date(d.timestamp).getTime() / 1000,
                    value: Number(d.price)
                }))
                const unique = Array.from(new Map(formatted.map(item => [item.time, item])).values())
                setChartData(unique)
            }
        }
        fetchData()
    }, [symbol])

    // 2. Realtime Subscription
    useEffect(() => {
        const channel = supabase
            .channel(`market_data:${symbol}`)
            .on(
                'postgres_changes',
                {
                    event: 'INSERT',
                    schema: 'public',
                    table: 'market_data',
                    filter: `symbol=eq.${symbol}`,
                },
                (payload) => {
                    const newPoint = payload.new
                    setChartData(prev => {
                        const point = {
                            time: new Date(newPoint.timestamp).getTime() / 1000,
                            value: Number(newPoint.price)
                        }
                        // Prevent duplicates and ensure sorting
                        const newMap = new Map(prev.map(p => [p.time, p]))
                        newMap.set(point.time, point)
                        return Array.from(newMap.values()).sort((a, b) => (a.time as number) - (b.time as number))
                    })
                }
            )
            .subscribe()

        return () => {
            supabase.removeChannel(channel)
        }
    }, [symbol])

    // 3. Render Chart
    useEffect(() => {
        let chart: IChartApi | null = null;
        let resizeObserver: ResizeObserver | null = null;

        const initChart = async () => {
            if (!chartContainerRef.current) return

            // Dynamic import to avoid SSR issues
            const { createChart, AreaSeries } = await import('lightweight-charts')
            // Import type locally if needed, or cast as any for simplicity in dynamic import context
            // But since we use dynamic import, we can't easily use the generic types from the module at top level 
            // without importing them at top level. We already import IChartApi, ISeriesApi. 
            // Let's just cast to any or Time if we can import it.

            // Time type is exported by lightweight-charts but we are in dynamic import context for the factory.
            // We can import Time from the top level safely as it's just a type.

            const chartOptions = {
                layout: {
                    textColor: isDark ? '#D9D9D9' : 'black',
                    background: { type: ColorType.Solid, color: isDark ? '#111827' : 'white' },
                },
                grid: {
                    vertLines: { color: isDark ? '#374151' : '#e0e0e0' },
                    horzLines: { color: isDark ? '#374151' : '#e0e0e0' },
                },
                width: chartContainerRef.current.clientWidth,
                height: 400,
            }

            chart = createChart(chartContainerRef.current, chartOptions)
            chartRef.current = chart

            const series = chart.addSeries(AreaSeries, {
                lineColor: '#2962FF',
                topColor: '#2962FF',
                bottomColor: 'rgba(41, 98, 255, 0.28)',
            })
            seriesRef.current = series
            // @ts-expect-error - Lightweight charts dynamic type issue
            series.setData(chartData)
            chart.timeScale().fitContent()

            resizeObserver = new ResizeObserver(entries => {
                if (entries.length === 0 || entries[0].target !== chartContainerRef.current) { return; }
                const newRect = entries[0].contentRect;
                chart?.applyOptions({ width: newRect.width, height: newRect.height });
            });
            resizeObserver.observe(chartContainerRef.current);
        }

        initChart()

        return () => {
            if (chart) {
                chart.remove()
                chart = null
            }
            if (resizeObserver) {
                resizeObserver.disconnect()
            }
        }
    }, [isDark]) // eslint-disable-line react-hooks/exhaustive-deps

    // 4. Update Data
    useEffect(() => {
        if (seriesRef.current && chartData.length > 0) {
            // @ts-expect-error - Lightweight charts dynamic type issue
            seriesRef.current.setData(chartData)
        }
    }, [chartData])

    return (
        <div className="w-full h-[400px] border border-gray-800 rounded-lg overflow-hidden relative">
            <div ref={chartContainerRef} className="w-full h-full" />
            <div className="absolute top-4 left-4 bg-black/50 px-3 py-1 rounded text-sm text-gray-300 pointer-events-none">
                {symbol} Live
            </div>
        </div>
    )
}
