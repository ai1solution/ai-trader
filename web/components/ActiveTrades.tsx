'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Clock } from 'lucide-react'

// Assuming trades table schema
interface Trade {
    id: number
    symbol: string
    side: string
    entry_price: number
    quantity: number
    entry_time: string
    pnl?: number // Unrealized PnL could be calculated if we had live price
}

export default function ActiveTrades({ refreshTrigger }: { refreshTrigger: number }) {
    const [trades, setTrades] = useState<Trade[]>([])

    useEffect(() => {
        const fetchTrades = async () => {
            const { data } = await supabase
                .from('trades')
                .select('*')
                .is('exit_time', null)
                .order('entry_time', { ascending: false })

            if (data) setTrades(data)
        }

        fetchTrades()
        const interval = setInterval(fetchTrades, 30000)
        return () => clearInterval(interval)
    }, [refreshTrigger])

    if (trades.length === 0) {
        return (
            <div className="text-center p-8 text-gray-500 bg-gray-900 border border-gray-800 rounded-xl">
                No active positions
            </div>
        )
    }

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                <h3 className="font-semibold text-white">Active Positions</h3>
                <span className="text-xs bg-blue-900/30 text-blue-400 px-2 py-1 rounded-full">{trades.length} Open</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-400 uppercase bg-gray-950/50">
                        <tr>
                            <th className="px-4 py-3">Symbol</th>
                            <th className="px-4 py-3">Side</th>
                            <th className="px-4 py-3">Entry</th>
                            <th className="px-4 py-3">Time</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                        {trades.map((trade) => (
                            <tr key={trade.id} className="hover:bg-gray-800/30">
                                <td className="px-4 py-3 font-medium text-white">{trade.symbol}</td>
                                <td className="px-4 py-3">
                                    <span className={`px-2 py-0.5 rounded text-xs ${trade.side === 'BUY' ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'}`}>
                                        {trade.side}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-gray-300 font-mono">${Number(trade.entry_price).toFixed(4)}</td>
                                <td className="px-4 py-3 text-gray-500">
                                    <div className="flex items-center gap-1">
                                        <Clock size={12} />
                                        {new Date(trade.entry_time).toLocaleTimeString()}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
