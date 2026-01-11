"""
Optimizer Module.
Runs multiple strategy profiles against shared historical data to find the best configuration.
"""
import sys
import yaml
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from v4.config.config import load_config
from v4.runner.runner import STRATEGY_MAP
from v4.engine.engine import TradingEngine
from v4.data.historical_feed import HistoricalFeed

async def run_optimization(config_path: str, profiles_path: str):
    # 1. Load Configurations
    config = load_config(config_path)
    
    try:
        with open(profiles_path, "r") as f:
            profiles_data = yaml.safe_load(f)
            profiles = profiles_data.get("profiles", [])
    except FileNotFoundError:
        print(f"Profiles file not found: {profiles_path}")
        return

    if not profiles:
        print("No profiles found to optimize.")
        return

    print(f"[Optimizer] Loaded {len(profiles)} profiles.")
    
    # Parse Dates
    start_dt = datetime.fromisoformat(config.start_date.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(config.end_date.replace("Z", "+00:00"))

    # 2. Iterate per Symbol (Fetch Data ONCE)
    for symbol in config.symbols:
        print(f"\n[Optimizer] Processing {symbol}...")
        
        # A. Fetch Data Shared
        feed = HistoricalFeed(symbol, start_dt, end_dt)
        await feed.initialize()
        
        shared_ticks = feed.get_ticks()
        if not shared_ticks:
            print(f"No data for {symbol}. Skipping.")
            continue
            
        print(f"[Data] Loaded {len(shared_ticks)} ticks for shared use.")
        
        # B. Setup Engines
        engines = []
        for profile in profiles:
            strat_name = profile["strategy"]
            strat_class = STRATEGY_MAP.get(strat_name)
            
            if not strat_class:
                print(f"Unknown strategy in profile: {profile['name']}")
                continue
                
            strategy = strat_class(profile["name"], profile["params"])
            # Initialize with $100 capital
            engine = TradingEngine(symbol, strategy, initial_balance=100.0)
            engines.append(engine)
            
        if not engines:
            continue
            
        # C. Run Simulation (Shared Loop)
        print(f"[Sim] Running {len(engines)} profiles concurrently on {symbol}...")
        
        start_time = datetime.now()
        
        for tick in shared_ticks:
            for engine in engines:
                engine.on_tick(tick)
                
        duration = datetime.now() - start_time
        print(f"[Sim] Complete in {duration.total_seconds():.2f}s")
        
        # D. Results
        best_pnl = -float('inf')
        best_profile = None
        
        print("\n--- Results for {symbol} ---")
        print(f"{'Profile':<25} | {'PnL ($)':<10} | {'Trades':<8} | {'Win Rate'}")
        print("-" * 60)
        
        for engine in engines:
            pnl = engine.total_pnl
            trades = len(engine.trades)
            winners = len([t for t in engine.trades if t["pnl"] > 0])
            win_rate = (winners / trades * 100) if trades > 0 else 0.0
            
            print(f"{engine.strategy.name:<25} | {pnl:>10.2f} | {trades:>8} | {win_rate:>5.1f}%")
            
            if pnl > best_pnl:
                best_pnl = pnl
                best_profile = engine.strategy.name
                
        print(f"\nBest Profile for {symbol}: {best_profile} (${best_pnl:.2f})")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="v4/config.yaml")
    parser.add_argument("--profiles", default="v4/config/profiles.yaml")
    
    args = parser.parse_args()
    
    asyncio.run(run_optimization(args.config, args.profiles))
