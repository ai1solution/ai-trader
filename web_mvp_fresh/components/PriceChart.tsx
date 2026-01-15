'use client'

import { createChart, ColorType, IChartApi, ISeriesApi, Time, AreaSeries } from 'lightweight-charts'
import { useEffect, useRef, useState } from 'react'
import { Box, Button, ButtonGroup, Flex, Spinner, useColorModeValue } from '@chakra-ui/react'

interface ChartDataPoint {
    time: number // Unix timestamp
    value: number
}

interface PriceChartProps {
    data: ChartDataPoint[]
    symbol: string
    color?: string
}

export default function PriceChart({ data, symbol, color = '#4f46e5' }: PriceChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<IChartApi | null>(null)
    const seriesRef = useRef<ISeriesApi<"Area"> | null>(null)
    const [timeRange, setTimeRange] = useState('ALL')

    // Initialize Chart
    useEffect(() => {
        if (!chartContainerRef.current) return

        const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth })
            }
        }

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#9ca3af',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            timeScale: {
                timeVisible: true,
                secondsVisible: true,
            },
        })

        chartRef.current = chart

        // v5 API: use addSeries(AreaSeries, options)
        const newSeries = chart.addSeries(AreaSeries, {
            lineColor: color,
            topColor: color, // gradient start
            bottomColor: 'rgba(79, 70, 229, 0.05)', // gradient end
            lineWidth: 2,
        })

        seriesRef.current = newSeries

        // Initial data
        const sortedData = [...data].sort((a, b) => a.time - b.time)

        // De-duplicate time
        const uniqueData = []
        const seenTimes = new Set()
        for (const point of sortedData) {
            if (!seenTimes.has(point.time)) {
                uniqueData.push({ time: point.time as Time, value: point.value })
                seenTimes.add(point.time)
            }
        }

        newSeries.setData(uniqueData)
        chart.timeScale().fitContent()

        window.addEventListener('resize', handleResize)

        return () => {
            window.removeEventListener('resize', handleResize)
            chart.remove()
        }
    }, []) // Initialize once

    // Update Data
    useEffect(() => {
        if (seriesRef.current && data.length > 0) {
            const sortedData = [...data].sort((a, b) => a.time - b.time)
            const uniqueData = []
            const seenTimes = new Set()
            for (const point of sortedData) {
                if (!seenTimes.has(point.time)) {
                    uniqueData.push({ time: point.time as Time, value: point.value })
                    seenTimes.add(point.time)
                }
            }

            seriesRef.current.setData(uniqueData)
        }
    }, [data])

    return (
        <Box
            w="full"
            bg="gray.900"
            p={4}
            rounded="xl"
            borderWidth="1px"
            borderColor="gray.800"
            position="relative"
        >
            <Flex justify="space-between" mb={4} align="center">
                <ButtonGroup size="xs" variant="outline" isAttached colorScheme="gray">
                    {['1H', '4H', '1D', 'ALL'].map((range) => (
                        <Button
                            key={range}
                            isActive={timeRange === range}
                            onClick={() => setTimeRange(range)}
                            _active={{ bg: 'whiteAlpha.200', color: 'white' }}
                        >
                            {range}
                        </Button>
                    ))}
                </ButtonGroup>
                <Button size="xs" variant="ghost" onClick={() => chartRef.current?.timeScale().fitContent()}>
                    Reset View
                </Button>
            </Flex>
            <div ref={chartContainerRef} style={{ width: '100%' }} />
        </Box>
    )
}
