import { clsx } from 'clsx';
import { Activity, AlertTriangle, CheckCircle, Ban } from 'lucide-react';

interface Props {
    status: string;
}

export function StatusBadge({ status }: Props) {
    const styles = {
        STARTING: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
        RUNNING: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
        STOPPED: 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20',
        ERROR: 'bg-red-500/10 text-red-500 border-red-500/20',
    };

    const icons = {
        STARTING: Activity,
        RUNNING: CheckCircle,
        STOPPED: Ban,
        ERROR: AlertTriangle,
    };

    const s = status as keyof typeof styles;
    const Icon = icons[s] || Activity;

    return (
        <div className={clsx(
            "flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium uppercase tracking-wider",
            styles[s] || styles.STOPPED
        )}>
            <Icon className="w-3 h-3" />
            {status}
        </div>
    );
}
