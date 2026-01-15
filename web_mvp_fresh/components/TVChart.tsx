"use client";

import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, LineData, AreaSeries, Time } from 'lightweight-charts';
import { RefreshCw } from "lucide-react";

interface TVChartProps {
    data: { time: number; value: number }[]; // time is unix timestamp (seconds)
    colors?: {
        backgroundColor?: string;
        lineColor?: string;
        textColor?: string;
        areaTopColor?: string;
        areaBottomColor?: string;
    };
    height?: number;
}

export const TVChart = ({
    data,
    colors = {
        backgroundColor: 'transparent',
        lineColor: '#3b82f6',
        textColor: '#71717a',
        areaTopColor: 'rgba(59, 130, 246, 0.2)',
        areaBottomColor: 'rgba(59, 130, 246, 0.0)',
    },
    height = 400
}: TVChartProps) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

    // Initial Chart Creation
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: colors.backgroundColor },
                textColor: colors.textColor,
            },
            width: chartContainerRef.current.clientWidth,
            height: height,
            grid: {
                vertLines: { color: "#27272a" },
                horzLines: { color: "#27272a" },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: true,
                borderColor: "#27272a",
            },
            rightPriceScale: {
                borderColor: "#27272a",
            },
            crosshair: {
                vertLine: {
                    labelVisible: true,
                    style: 0, // Solid
                    color: "#52525b"
                },
            }
        });

        // V5 API: addSeries(AreaSeries, options)
        const newSeries = chart.addSeries(AreaSeries, {
            lineColor: colors.lineColor,
            topColor: colors.areaTopColor,
            bottomColor: colors.areaBottomColor,
            lineWidth: 2,
        });

        chartRef.current = chart;
        seriesRef.current = newSeries;

        // Initial Data
        if (data.length > 0) {
            // Ensure unique and sorted
            const cleanData = data.sort((a, b) => a.time - b.time);
            // Deduplicate by time
            const uniqueData = cleanData.filter((item, index, self) =>
                index === self.findIndex((t) => (
                    t.time === item.time
                ))
            ).map(d => ({ ...d, time: d.time as Time }));

            newSeries.setData(uniqueData);
            chart.timeScale().fitContent();
        }

        const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (chartRef.current) {
                chartRef.current.remove();
                chartRef.current = null;
            }
        };
    }, []);

    // Update Data efficiently
    useEffect(() => {
        if (!seriesRef.current || data.length === 0) return;

        // If data array replaces entirely vs incremental updates
        // For polling, we might just set data. 
        // LWC handles setData efficiently if sorted.
        const cleanData = [...data].sort((a, b) => a.time - b.time);

        // Deduplicate again to be safe
        const uniqueData = cleanData.filter((item, index, self) =>
            index === self.findIndex((t) => (
                t.time === item.time
            ))
        ).map(d => ({ ...d, time: d.time as Time }));

        seriesRef.current.setData(uniqueData);

        // Logic to keep view near active price?
        // chartRef.current?.timeScale().scrollToRealTime(); 
    }, [data, colors]);

    if (!data || data.length === 0) {
        return (
            <div className="h-[400px] w-full flex items-center justify-center bg-zinc-950/50 border border-zinc-800 rounded-lg animate-pulse">
                <div className="flex flex-col items-center gap-2 text-zinc-500">
                    <RefreshCw className="w-6 h-6 animate-spin" />
                    <span>Waiting for market data...</span>
                </div>
            </div>
        );
    }

    return (
        <div ref={chartContainerRef} className="w-full relative" style={{ height: height }} />
    );
};
