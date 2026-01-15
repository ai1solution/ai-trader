import { Badge } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

interface Props {
    symbol: string;
    price?: number;
    status: string;
    lastUpdated: string;
}

export function ProductHeader({ symbol, price, status, lastUpdated }: Props) {
    return (
        <div className="w-full flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 mb-6 bg-zinc-900/40 border border-zinc-800 backdrop-blur rounded-xl">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                    <span className="font-bold text-blue-500">{symbol.split('/')[0].substring(0, 1)}</span>
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">{symbol}</h1>
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <span>PERPETUAL</span>
                        <span>•</span>
                        <span>BINANCE</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-6">
                <div className="flex flex-col items-end">
                    <span className="text-xs text-zinc-500 uppercase font-medium mb-1">Status</span>
                    <StatusBadge status={status} />
                </div>

                <div className="flex flex-col items-end min-w-[120px]">
                    <span className="text-xs text-zinc-500 uppercase font-medium mb-1">Mark Price</span>
                    <div className="text-3xl font-mono font-bold text-white tracking-tighter">
                        ${price?.toFixed(2) || '--'}
                    </div>
                    <span className="text-[10px] text-zinc-600 font-mono">
                        Last Upd: {lastUpdated}
                    </span>
                </div>
            </div>
        </div>
    );
}
