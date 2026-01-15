import { ArrowDownRight, ArrowUpRight, LucideIcon } from 'lucide-react'

interface StatsCardProps {
    title: string
    value: string
    change?: string
    isPositive?: boolean
    icon: LucideIcon
}

export default function StatsCard({ title, value, change, isPositive, icon: Icon }: StatsCardProps) {
    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
            <div className="flex items-center justify-between mb-4">
                <span className="text-gray-400 text-sm font-medium">{title}</span>
                <div className="p-2 bg-gray-800 rounded-lg text-blue-400">
                    <Icon size={20} />
                </div>
            </div>
            <div className="flex items-baseline gap-2">
                <h3 className="text-2xl font-bold text-white">{value}</h3>
                {change && (
                    <span className={`flex items-center text-xs font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isPositive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        {change}
                    </span>
                )}
            </div>
        </div>
    )
}
