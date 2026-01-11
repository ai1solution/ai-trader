"""
Strategy Optimizer (Small Cap - $50)

Runs focused grid search to find MAX PROFIT parameters for a $50 account.
Uses Jan 8-15 2024 (ETF Approval Volatility) to find high-performance params.
Logging is DISABLED for maximum speed.

Usage:
    python optimize_strategies.py
"""

import itertools
import pandas as pd
import os
import shutil
from rich.console import Console
from rich.table import Table
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed

# Import engine components
from engine import EngineConfig, TradingEngine
from engine.logger import EngineLogger
from engine.market_data import HistoricalFeed
from historical_runner import fetch_historical_data

console = Console()

# Optimization Parameters
TEST_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"] 
START_DATE = "2024-01-08" # ETF Approval Week (High Volatility)
END_DATE = "2024-01-15"

# MID-RANGE Parameter Grid (Aggressive but Smart)
PARAM_GRID = {
    "arm_velocity_threshold": [0.004, 0.006, 0.008],   # 0.4% - 0.8%
    "arm_persistence_ticks": [4, 8, 12],               # Quick to Medium confirm
    "trailing_stop_pct": [0.015, 0.025, 0.04],         # Tight to Wide stops
    "partial_take_pct_trending": [0.005, 0.010],       # Quick vs Big takes
}

def generate_configs() -> List[Dict]:
    """Generate all combinations of parameters."""
    keys = PARAM_GRID.keys()
    values = PARAM_GRID.values()
    combinations = list(itertools.product(*values))
    
    configs = []
    for combo in combinations:
        params = dict(zip(keys, combo))
        # Fixed/Default Parameters for $50 Sizing
        params["position_size_usd"] = 50.0 # User limitation
        params["arm_timeout_seconds"] = 60.0
        params["velocity_lookback_ticks"] = 15
        params["acceleration_window_ticks"] = 5
        
        # Risk Management
        params["atr_stop_multiplier"] = 2.0 
        params["atr_period_ticks"] = 30
        
        # Profit Taking
        params["partial_take_pct_ranging"] = 0.005 # 0.5% in range
        params["post_partial_trail_reduction"] = 0.5
        
        # Drawdown Protection
        params["loser_suppression_enabled"] = True
        params["loser_streak_threshold"] = 2
        params["extended_cooldown_multiplier"] = 5.0
        params["cooldown_duration_seconds"] = 120.0
        params["replay_tick_interval_seconds"] = 2.0
        
        configs.append(params)
    
    return configs

def evaluate_config(params: Dict, candles_map: Dict[str, pd.DataFrame]) -> Dict:
    """Evaluate a single configuration across all test coins."""
    # Debug print to confirm worker started
    # print(f"DEBUG: Starting config with vel={params['arm_velocity_threshold']}")
    
    config = EngineConfig(**params)
    
    total_pnl = 0.0
    total_trades = 0
    wins = 0
    
    for symbol, candles in candles_map.items():
        # DISABLE LOGGING for speed (log_file=None)
        logger = EngineLogger(log_file=None, log_level="ERROR") 
        
        engine = TradingEngine(symbol=symbol, config=config, logger=logger)
        
        feed = HistoricalFeed(
            candles_df=candles,
            tick_interval_seconds=config.replay_tick_interval_seconds
        )
        
        while feed.has_more_data():
            tick = feed.get_next_tick()
            if tick:
                engine.on_tick(tick)
        
        stats = engine.get_statistics()
        total_pnl += stats['total_pnl']
        total_trades += stats['total_trades']
        wins += stats['winning_trades']

    # Metrics
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    # ROI based on Total Capital Deployed (Worst case all 3 positions open)
    invested_capital = len(TEST_COINS) * config.position_size_usd
    roi_pct = (total_pnl / invested_capital) * 100
    
    return {
        "params": params,
        "total_pnl": total_pnl,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "roi_pct": roi_pct
    }

def main():
    console.print("[bold blue]Starting Small Cap ($50) Strategy Optimization...[/bold blue]")
    console.print(f"[yellow]Period: {START_DATE} to {END_DATE} (ETF Volatility Week)[/yellow]")
    
    # 1. Pre-fetch Data
    console.print("Loading historical data...")
    candles_map = {}
    for symbol in TEST_COINS:
        candles_map[symbol] = fetch_historical_data(symbol, START_DATE, END_DATE)
    
    # 2. Generate
    configs = generate_configs()
    console.print(f"Testing {len(configs)} configurations on {len(TEST_COINS)} coins...")
    
    # 3. Run
    results = []
    max_workers = 4 # Reduced from 6 for stability
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(evaluate_config, cfg, candles_map): cfg for cfg in configs}
        
        from rich.progress import track
        for future in track(as_completed(futures), total=len(configs), description="Optimizing..."):
             try:
                res = future.result()
                results.append(res)
             except Exception as e:
                 console.print(f"[red]Error in optimization task: {e}[/red]")
    
    # 4. Analysis
    # Sort by Total PnL (Maximizing Profit)
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    table = Table(title=f"Top 5 Profitable Configs ($50 Size)")
    table.add_column("Rank")
    table.add_column("PnL $", style="green")
    table.add_column("ROI %")
    table.add_column("Trades")
    table.add_column("Win %")
    table.add_column("Vel (Persist)")
    table.add_column("Trail Stop")
    
    for i, res in enumerate(results[:5]):
        p = res['params']
        table.add_row(
            str(i+1),
            f"${res['total_pnl']:.2f}",
            f"{res['roi_pct']:.2f}%",
            str(res['total_trades']),
            f"{res['win_rate']:.1f}%",
            f"{p['arm_velocity_threshold']} ({p['arm_persistence_ticks']})",
            f"{p['trailing_stop_pct']}"
        )
    
    console.print(table)
    
    best = results[0]
    console.print(f"\n[bold green]MAX PROFIT CONFIGURATION (${best['total_pnl']:.2f}):[/bold green]")
    console.print(best['params'])
    
    if best['total_pnl'] > 0:
        console.print("\n[bold green]PROFITABLE STRATEGY FOUND![/bold green]")
    else:
        console.print("\n[bold red]Strategy still net negative. Try wider params.[/bold red]")

if __name__ == "__main__":
    main()
