"""
Async Parallel Runner.
Runs multiple TradingEngines concurrently.
"""
import asyncio
from datetime import datetime
from typing import List, Dict
import pandas as pd

from ..config.config import RunnerConfig
from ..engine.engine import TradingEngine
from ..data.historical_feed import HistoricalFeed
from ..data.live_feed import LiveFeed
from ..strategies.momentum import MomentumStrategy
from ..strategies.mean_reversion import MeanReversionStrategy
from ..strategies.trend_follow import TrendFollowingStrategy
from ..strategies.breakout import BreakoutStrategy
from ..engine.universe import UniverseSelector

STRATEGY_MAP = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "trend_follow": TrendFollowingStrategy,
    "breakout": BreakoutStrategy
}

from ..engine.regime import RegimeClassifier
from ..engine.portfolio import Portfolio

class ParallelRunner:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.engines: List[TradingEngine] = []
        self.feeds: List[any] = [] # List of Feeds
        self.running = False
        self.log_queue = asyncio.Queue()
        self.regime_classifier = RegimeClassifier()
        self.portfolio = Portfolio()
        
    async def setup(self):
        """
        Initialize Engines and Feeds.
        """
        print(f"[Runner] Setting up... Mode: {self.config.mode}")
        print(f"[Flags] Universe:{self.config.use_universe} Regime:{self.config.use_regime} "
              f"Portfolio:{self.config.use_portfolio} Protection:{self.config.use_protection}")
        
        # Parse Dates for Backtest
        start_dt = datetime.fromisoformat(self.config.start_date.replace("Z", "+00:00")) if self.config.mode == "backtest" else None
        end_dt = datetime.fromisoformat(self.config.end_date.replace("Z", "+00:00")) if self.config.mode == "backtest" else None
        
        # 1. Universe Selection
        if self.config.use_universe:
            selector = UniverseSelector(self.config.universe)
            selected_symbols = await selector.select_symbols(self.config.symbols, refernece_time=start_dt or datetime.now())
            await selector.cleanup()
        else:
            selected_symbols = self.config.symbols
            
        print(f"[Runner] Selected {len(selected_symbols)} symbols: {selected_symbols}")
        
        # 2. Init Shared Components
        if self.config.use_regime:
            self.regime_classifier = RegimeClassifier()
            # PRE-FETCH REGIME DATA
            print("[Runner] Pre-fetching Regime Data (Daily)...")
            
            # Determine range
            # If backtest, we need start date - 60 days
            # If live, we need now - 60 days
            
            ref_end = end_dt if end_dt else datetime.now()
            ref_start = (start_dt if start_dt else datetime.now()) - pd.Timedelta(days=80) 
            
            # Use a specialized provider for fetching? Or use the classifier's provider?
            # Classifier helper usage:
            prov = self.regime_classifier.provider
            
            for symbol in selected_symbols:
                try:
                   # Fetch Daily
                   df = await prov.fetch_ohlcv(symbol, '1d', start_time=ref_start, end_time=ref_end)
                   self.regime_classifier.preload_data(symbol, df)
                except Exception as e:
                   print(f"[Runner] Failed to fetch regime data for {symbol}: {e}")
            
        else:
             self.regime_classifier = None
             
        if self.config.use_portfolio:
            self.portfolio = Portfolio()
        else:
             self.portfolio = None
        
        for symbol in selected_symbols:
            for strat_conf in self.config.strategies:
                # 1. Create Strategy
                strat_class = STRATEGY_MAP.get(strat_conf.name)
                if not strat_class:
                    print(f"Unknown strategy: {strat_conf.name}")
                    continue
                    
                strategy = strat_class(strat_conf.name, strat_conf.params)
                
                # 2. Create Engine
                engine = TradingEngine(
                    symbol, 
                    strategy, 
                    initial_balance=100.0, 
                    log_queue=self.log_queue,
                    regime_classifier=self.regime_classifier,
                    portfolio=self.portfolio,
                    use_protection=self.config.use_protection
                )
                self.engines.append(engine)
                
                # 3. Create Feed (One per engine? Or One per symbol?)
                # For simplicity, each engine gets its own feed instance to avoid state sharing issues in simple architecture.
                
                if self.config.mode == "backtest":
                    feed = HistoricalFeed(symbol, start_dt, end_dt)
                    await feed.initialize() # Pre-load data
                    self.feeds.append(feed)
                else:
                    feed = LiveFeed(symbol)
                    self.feeds.append(feed)
                    
        print(f"[Runner] Setup complete. {len(self.engines)} engines ready.")

    async def run_loop(self):
        """
        Main execution loop.
        """
        self.running = True
        
        # Async Loop
        while self.running:
            tasks = []
            
            # 1. Fetch Ticks for all feeds
            active_feeds = 0
            
            for i, engine in enumerate(self.engines):
                feed = self.feeds[i]
                tick = await feed.get_next_tick()
                
                if tick:
                    active_feeds += 1
                    # Await engine processing (since it includes async regime check now)
                    await engine.on_tick(tick)
                    
            if active_feeds == 0 and self.config.mode == "backtest":
                print("[Runner] All feeds exhausted.")
                self.running = False
                break
            elif active_feeds == 0 and self.config.mode == "paper":
                # Wait a bit if no data
                await asyncio.sleep(0.1)
                
            # Allow other tasks (Dashboard) to run
            await asyncio.sleep(0) # Yield
            
    def get_stats(self) -> List[Dict]:
        stats = []
        for engine in self.engines:
            stats.append({
                "symbol": engine.symbol,
                "strategy": engine.strategy.name,
                "state": engine.state,
                "balance": engine.balance,
                "pnl": engine.total_pnl,
                "trades": len(engine.trades),
                "active": engine.position is not None,
                "price": engine.last_tick.price if engine.last_tick else 0.0
            })
        return stats

    async def cleanup(self):
        """
        Cleanup resources (e.g., closing sessions).
        """
        print("[Runner] Cleaning up...")
        for feed in self.feeds:
            if hasattr(feed, 'cleanup'):
                await feed.cleanup()
            elif hasattr(feed, 'close'):
                await feed.close()
        
        # Allow SSL transports to close gracefully on Windows
        await asyncio.sleep(0.25)
        
        print("[Runner] Cleanup complete.")
