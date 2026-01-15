'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import { Activity, Play, StopCircle, Terminal, TrendingUp, Wallet, DollarSign, BarChart2, RefreshCw } from 'lucide-react'
import Navbar from '@/components/Navbar'
import PriceChart from '@/components/PriceChart'
import StatsCard from '@/components/StatsCard'
import ActiveTrades from '@/components/ActiveTrades'
import RunList from '@/components/RunList'
import { useDashboardStats } from '@/hooks/useDashboardStats'

interface RunData {
  id: string
  status: string
  symbols: string[]
  engine_version: string
  created_at: string
}

export default function Dashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const router = useRouter()
  const [activeRun, setActiveRun] = useState<RunData | null>(null)
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT') // Default or from run
  const [showStartModal, setShowStartModal] = useState(false)
  const [launchSymbols, setLaunchSymbols] = useState('BTC/USDT')
  const [launchVersion, setLaunchVersion] = useState('v4')
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // Use custom hook for real data
  const { stats, isLoading, refresh: refreshStats } = useDashboardStats()

  const handleManualRefresh = () => {
    refreshStats()
    setRefreshTrigger(prev => prev + 1)
  }

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        router.push('/login')
      } else {
        setIsAuthenticated(true)
      }
    }
    checkAuth()
  }, [router])

  useEffect(() => {
    // Fetch latest active run
    const fetchActiveRun = async () => {
      const { data } = await supabase
        .from('runs')
        .select('*')
        .eq('status', 'RUNNING')
        .order('created_at', { ascending: false })
        .limit(1)
        .single()

      if (data) {
        setActiveRun(data)
        // If run has symbols that include current, keep it, else switch to first
        if (data.symbols && Array.isArray(data.symbols) && data.symbols.length > 0) {
          if (!data.symbols.includes(selectedSymbol)) {
            setSelectedSymbol(data.symbols[0])
          }
        }
      } else {
        setActiveRun(null)
      }
    }

    fetchActiveRun()

    const channel = supabase.channel('dashboard_runs')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'runs' }, fetchActiveRun)
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [selectedSymbol, refreshTrigger])

  const handleStartRun = async () => {
    const symbols = launchSymbols.split(',').map(s => s.trim().toUpperCase())
    await supabase.from('commands').insert({
      command: 'START_RUN',
      payload: { version: launchVersion, config_overrides: { symbols } }
    })
    setShowStartModal(false)
    setLaunchSymbols('')
    // Trigger generic refresh to maybe catch PENDING status (though manager needs time)
  }

  if (!isAuthenticated) return null

  return (
    <div className="min-h-screen bg-[#0b0e11] text-gray-100 font-sans selection:bg-blue-500/30">
      <Navbar />

      <main className="max-w-[1600px] mx-auto px-4 py-6 space-y-6">

        {/* Top Bar: Stats & Controls */}
        <div className="flex flex-col xl:flex-row gap-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 flex-1">
            <StatsCard
              title="Total PnL"
              value={`$${stats.totalPnL.toFixed(2)}`}
              change={stats.totalPnL !== 0 ? (stats.totalPnL > 0 ? "+ROI" : "-ROI") : undefined}
              isPositive={stats.totalPnL >= 0}
              icon={DollarSign}
            />
            <StatsCard
              title="Active Positions"
              value={stats.activeTrades.toString()}
              icon={Activity}
            />
            <StatsCard
              title="Win Rate"
              value={`${stats.winRate.toFixed(1)}%`}
              isPositive={stats.winRate > 50}
              icon={TrendingUp}
            />
            <StatsCard
              title="Capital Deployed"
              value={`$${stats.capitalDeployed.toString()}`}
              icon={Wallet}
            />
          </div>

          {/* Quick Control Panel */}
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 min-w-[300px] flex flex-col justify-center gap-4">
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-400">
                <span>Engine Status</span>
              </div>
              <span className={activeRun ? "text-emerald-400 font-bold" : "text-gray-500"}>
                {activeRun ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowStartModal(true)}
                className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition-colors"
              >
                <Play size={16} /> New Session
              </button>
              <button
                onClick={handleManualRefresh}
                className={`px-3 ${isLoading ? 'bg-gray-800' : 'bg-gray-800 hover:bg-gray-700'} text-gray-300 rounded-lg transition-colors border border-gray-700 flex items-center justify-center`}
                disabled={isLoading}
                title="Refresh Data"
              >
                <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
              </button>
              {activeRun && (
                <button className="px-3 bg-red-900/20 hover:bg-red-900/40 text-red-500 rounded-lg transition-colors border border-red-900/50">
                  <StopCircle size={18} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Main Workspace Split */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 h-[calc(100vh-280px)] min-h-[600px]">

          {/* Left: Chart & Market (8 cols) */}
          <div className="xl:col-span-8 flex flex-col gap-6 h-full">
            {/* Chart Container */}
            <div className="flex-1 bg-gray-900 border border-gray-800 rounded-xl p-1 flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <BarChart2 size={18} className="text-blue-400" />
                    <h2 className="font-bold text-gray-200">{selectedSymbol}</h2>
                  </div>
                  {activeRun?.symbols && (
                    <div className="flex gap-1">
                      {activeRun.symbols.map((s: string) => (
                        <button
                          key={s}
                          onClick={() => setSelectedSymbol(s)}
                          className={`px-2 py-1 text-xs rounded ${selectedSymbol === s ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-xs text-gray-500">Live Feed</div>
              </div>
              <div className="flex-1 relative w-full h-full min-h-[400px]">
                <PriceChart symbol={selectedSymbol} />
              </div>
            </div>
          </div>

          {/* Right: Positions & Logs (4 cols) */}
          <div className="xl:col-span-4 flex flex-col gap-6 h-full overflow-hidden">

            {/* Active Positions Table */}
            <div className="flex-1 bg-gray-900 border border-gray-800 rounded-xl flex flex-col overflow-hidden">
              <ActiveTrades refreshTrigger={refreshTrigger} />
            </div>

            {/* Recent Activity / System Log Placeholder */}
            <div className="h-1/3 bg-gray-900/50 border border-gray-800 rounded-xl p-4 flex flex-col">
              <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                <Terminal size={14} /> System Activity
              </h3>
              <div className="flex-1 overflow-y-auto space-y-2 text-xs font-mono">
                {activeRun ? (
                  <>
                    <div className="text-emerald-400">[SYSTEM] Engine v4 started successfully</div>
                    <div className="text-gray-400">[INFO] Loaded regime data for {selectedSymbol}</div>
                    <div className="text-gray-400">[INFO] Monitoring market conditions...</div>
                  </>
                ) : (
                  <div className="text-gray-600 italic">System idle. Waiting for commands.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Start Modal */}
      {showStartModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-[#111827] border border-gray-700 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold mb-1 text-white">Start Trading Session</h3>
            <p className="text-gray-400 text-sm mb-6">Configure the V4 Engine parameters.</p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase mb-2">Engine Version</label>
                <select
                  value={launchVersion}
                  onChange={e => setLaunchVersion(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 font-mono"
                >
                  <option value="v4">V4 (Latest - Parallel)</option>
                  <option value="v3">V3 (Live Mock)</option>
                  <option value="v2">V2 (Modern)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase mb-2">Trading Pairs</label>
                <input
                  type="text"
                  value={launchSymbols}
                  onChange={e => setLaunchSymbols(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 font-mono"
                  placeholder="BTC/USDT, ETH/USDT"
                />
                <p className="text-xs text-gray-600 mt-2">Separate multiple pairs with commas.</p>
              </div>
            </div>

            <div className="flex gap-3 mt-8">
              <button
                onClick={() => setShowStartModal(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 py-3 rounded-lg transition-colors font-medium border border-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleStartRun}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-lg font-medium transition-colors shadow-lg shadow-blue-900/20"
              >
                Launch Engine
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
