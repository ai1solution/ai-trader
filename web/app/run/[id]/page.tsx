/* eslint-disable @typescript-eslint/no-explicit-any */
'use client'
import { useEffect, useState, useRef, use } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Clock, Terminal } from 'lucide-react'
import Link from 'next/link'

export default function RunDetails({ params }: { params: Promise<{ id: string }> }) {
    const router = useRouter()
    const resolvedParams = use(params)
    const id = resolvedParams.id

    // Use proper types or Record<string, any> to satisfy linter
    const [run, setRun] = useState<Record<string, any> | null>(null)
    const [logs, setLogs] = useState<Record<string, any>[]>([])
    const [trades, setTrades] = useState<Record<string, any>[]>([])
    const logsEndRef = useRef<HTMLDivElement>(null)

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [logs])

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            if (!session) router.push('/login')
        })

        const fetchData = async () => {
            const { data: runData } = await supabase.from('runs').select('*').eq('id', id).single()
            setRun(runData)

            // Fetch logs
            const { data: logData } = await supabase
                .from('logs')
                .select('*')
                .eq('run_id', id)
                .order('created_at', { ascending: true })
                .limit(500) // Initial load limit

            if (logData) setLogs(logData)

            // Fetch trades
            const { data: tradeData } = await supabase
                .from('trades')
                .select('*')
                .eq('run_id', id)
                .order('entry_time', { ascending: false })

            if (tradeData) setTrades(tradeData)
        }

        if (id) {
            fetchData()

            const channel = supabase
                .channel(`run:${id}`)
                .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'logs', filter: `run_id=eq.${id}` }, payload => {
                    setLogs(current => [...current, payload.new])
                })
                .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'runs', filter: `id=eq.${id}` }, payload => {
                    setRun(payload.new)
                })
                .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'trades', filter: `run_id=eq.${id}` }, payload => {
                    setTrades(current => [payload.new, ...current])
                })
                .subscribe()

            return () => { supabase.removeChannel(channel) }
        }
    }, [id, router])

    if (!run) return <div className="min-h-screen bg-gray-950 text-white p-8">Loading...</div>

    return (
        <main className="min-h-screen bg-gray-950 text-white p-6">
            <Link href="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6">
                <ArrowLeft size={16} /> Back to Dashboard
            </Link>

            <div className="flex justify-between items-start mb-6">
                <div>
                    <h1 className="text-2xl font-bold">{run.symbols?.join(', ')} <span className="text-gray-500 text-base font-normal">({run.engine_version})</span></h1>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                        <span className="flex items-center gap-1"><Clock size={14} /> Started: {new Date(run.start_time).toLocaleString()}</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${run.status === 'RUNNING' ? 'bg-emerald-900/40 text-emerald-400' : 'bg-gray-800'}`}>{run.status}</span>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-3xl font-bold text-emerald-400 font-mono">
                        ${run.result?.pnl?.toFixed(2) || "0.00"}
                    </div>
                    <div className="text-xs text-gray-500 uppercase tracking-widest">Total PnL</div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
                {/* Logs Terminal */}
                <div className="lg:col-span-2 bg-black border border-gray-800 rounded-xl flex flex-col font-mono text-sm overflow-hidden">
                    <div className="bg-gray-900 px-4 py-2 border-b border-gray-800 flex items-center gap-2 text-gray-400 text-xs">
                        <Terminal size={12} /> Live Console Output
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-1">
                        {logs.map(log => (
                            <div key={log.id} className="break-all">
                                <span className="text-gray-500 select-none mr-3">[{new Date(log.created_at).toLocaleTimeString()}]</span>
                                <span className={log.message.includes("ERROR") ? "text-red-400" : "text-gray-300"}>
                                    {log.message}
                                </span>
                            </div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                </div>

                {/* Trades List */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col overflow-hidden">
                    <div className="px-4 py-3 border-b border-gray-800 font-medium">Recent Trades</div>
                    <div className="flex-1 overflow-y-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="text-gray-500 border-b border-gray-800">
                                    <th className="p-3 font-normal">Symbol</th>
                                    <th className="p-3 font-normal">Side</th>
                                    <th className="p-3 font-normal text-right">PnL</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades.length === 0 ? (
                                    <tr><td colSpan={3} className="p-4 text-center text-gray-500">No trades yet</td></tr>
                                ) : trades.map(trade => (
                                    <tr key={trade.id} className="border-b border-gray-800/50 hover:bg-gray-800/50">
                                        <td className="p-3">{trade.symbol}</td>
                                        <td className={`p-3 ${trade.side === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{trade.side}</td>
                                        <td className={`p-3 text-right font-mono ${Number(trade.pnl) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            ${Number(trade.pnl).toFixed(2)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    )
}
