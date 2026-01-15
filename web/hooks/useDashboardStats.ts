import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export interface DashboardStats {
    totalPnL: number
    winRate: number
    activeTrades: number
    totalTrades: number
    capitalDeployed: number
}

export function useDashboardStats() {
    const [stats, setStats] = useState<DashboardStats>({
        totalPnL: 0,
        winRate: 0,
        activeTrades: 0,
        totalTrades: 0,
        capitalDeployed: 0 // Mocked for now unless we track it
    })

    const [isLoading, setIsLoading] = useState(false)

    const fetchStats = async () => {
        setIsLoading(true)
        try {
            // 1. Fetch Closed Trades for PnL & Win Rate (Optimized: limit to last 1000 or specific time range if needed)
            const { data: closedTrades } = await supabase
                .from('trades')
                .select('pnl')
                .not('exit_time', 'is', null)
                .limit(1000) // Performance limit

            // 2. Fetch Active Trades
            const { count: activeCount } = await supabase
                .from('trades')
                .select('*', { count: 'exact', head: true })
                .is('exit_time', null)

            if (closedTrades) {
                const totalPnL = closedTrades.reduce((acc, t) => acc + (Number(t.pnl) || 0), 0)
                const wins = closedTrades.filter(t => (Number(t.pnl) || 0) > 0).length
                const total = closedTrades.length
                const winRate = total > 0 ? (wins / total) * 100 : 0

                setStats({
                    totalPnL,
                    winRate,
                    activeTrades: activeCount || 0,
                    totalTrades: total,
                    capitalDeployed: (activeCount || 0) * 100 // Estimate active capital
                })
            }
        } catch (e) {
            console.error(e)
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchStats()

        // 30 Seconds Polling
        const interval = setInterval(fetchStats, 30000)

        // Realtime updates (Optional: keep or remove if polling is preferred for performance)
        // User requested "Fetch data every 30 second automatically".
        // Realtime might be too heavy if many trades. Let's rely on polling as requested to save resources.
        // const channel = supabase
        //     .channel('stats_realtime')
        //     .on('postgres_changes', { event: '*', schema: 'public', table: 'trades' }, fetchStats)
        //     .subscribe()

        return () => {
            clearInterval(interval)
            // supabase.removeChannel(channel)
        }
    }, [])

    return { stats, isLoading, refresh: fetchStats }
}
