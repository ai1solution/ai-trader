'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Server, ArrowRight } from 'lucide-react'
import Link from 'next/link'

interface Run {
    id: string
    status: string
    symbols: string[]
    engine_version: string
    created_at: string
}

export default function RunList() {
    const [runs, setRuns] = useState<Run[]>([])

    useEffect(() => {
        const fetchRuns = async () => {
            const { data } = await supabase
                .from('runs')
                .select('*')
                .order('created_at', { ascending: false })
                .limit(10) // Show last 10
            if (data) setRuns(data)
        }

        fetchRuns() // eslint-disable-line react-hooks/exhaustive-deps
        const channel = supabase.channel('run_list')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'runs' }, fetchRuns)
            .subscribe()
        return () => { supabase.removeChannel(channel) }
    }, [])

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                <h3 className="font-semibold text-white flex items-center gap-2">
                    <Server size={16} className="text-blue-400" /> Engine Instances
                </h3>
            </div>
            <div className="overflow-y-auto flex-1">
                {runs.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 text-sm">No engines found.</div>
                ) : (
                    <div className="divide-y divide-gray-800">
                        {runs.map(run => (
                            <Link
                                key={run.id}
                                href={`/run/${run.id}`}
                                className="block p-4 hover:bg-gray-800/50 transition-colors group"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-2">
                                        <span className={`w-2 h-2 rounded-full ${run.status === 'RUNNING' ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50' : 'bg-gray-600'}`} />
                                        <span className="font-medium text-gray-200">{run.engine_version.toUpperCase()}</span>
                                    </div>
                                    <span className="text-xs text-gray-500 font-mono">
                                        {new Date(run.created_at).toLocaleTimeString()}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <div className="text-gray-400">
                                        {run.symbols?.join(', ') || 'No Symbols'}
                                    </div>
                                    <div className="flex items-center text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <span className="text-xs mr-1">Details</span>
                                        <ArrowRight size={14} />
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
