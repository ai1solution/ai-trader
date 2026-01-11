"""
Dynamic Volatility Hunter (High Precision Edition)

Tracks a $50 simulated wallet trading Top 15 Recent Gainers/Volatile Coins.
Precision: 8 Decimal Points.
Strategies: 6 Variants covering Scalp, Swing, and Breakout.

Strategies:
1. MICRO_SCALP (0.12% Vel) - Quick 0.4% wins.
2. SNIPER      (0.15% Vel) - Precision 0.5% wins.
3. BREAKOUT    (0.20% Vel) - Fast momentum, wide trail.
4. MOMENTUM    (0.30% Vel) - Strong trend follow.
5. REVERSION   (0.40% Vel) - Fading exhaustions (Simulated via tight stops on reversal).
6. OPTIMIZED   (0.80% Vel) - Safe baseline.

Usage:
    python live_multi_strategy.py --coins 15
"""

import sys
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import threading
import queue
import json
import os
from datetime import timezone
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from engine import EngineConfig, TradingEngine
from engine.logger import EngineLogger
from engine.market_data import LiveFeed

console = Console()

# TOP 15 RESEARCHED COINS (Jan 8 Results)
# Sorted by Volatility & Recent Gains
VOLATILE_COINS_15 = [
    # Top Gainers / Movers
    "SUIUSDT", "SNXUSDT", "XRPUSDT", "INJUSDT", "AAVEUSDT",
    # High Volatility Memes
    "BONKUSDT", "WIFUSDT", "PEPEUSDT", "FLOKIUSDT", "MEMEUSDT", 
    "SHIBUSDT", "ORDIUSDT",
    # Steady Volatility
    "FILUSDT", "UNIUSDT", "TIAUSDT"
]

class Wallet:
    """Simulates a trading wallet."""
    def __init__(self, initial_balance: float = 50.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.lock = threading.Lock()
        self.history = [] 

    def update_pnl(self, pnl: float):
        with self.lock:
            self.balance += pnl
            self.history.append((time.time(), pnl))
            
    def get_balance(self) -> float:
        with self.lock:
            return self.balance
            
    def get_pnl_pct(self) -> float:
        with self.lock:
            return ((self.balance - self.initial_balance) / self.initial_balance) * 100

class StrategyConfig:
    def __init__(self, name: str, description: str, config: EngineConfig):
        self.name = name
        self.description = description
        self.config = config
        self.stats = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0
        })
        self.current_prices = {}

def create_strategies() -> List[StrategyConfig]:
    strategies = []
    
    # 1. MICRO_SCALP (Modified for Volatility)
    s1 = EngineConfig(
        arm_velocity_threshold=0.0050,  # Increased from 0.30% -> 0.50% (Noise Filter)
        arm_persistence_ticks=3,        # Increased from 2 -> 3
        trailing_stop_pct=0.006,        
        atr_stop_multiplier=1.5,
        partial_take_pct_trending=0.006,
        partial_take_pct_ranging=0.005,
        position_size_usd=10.0, 
        loser_suppression_enabled=True,
        cooldown_duration_seconds=60,    # Explicit 60s cooldown
        active_strategy="momentum"
    )
    strategies.append(StrategyConfig("MICRO_SCALP", "Quick", s1))
    
    # 2. SNIPER (Modified)
    s2 = EngineConfig(
        arm_velocity_threshold=0.0040, # Increased from 0.15% -> 0.40%
        arm_persistence_ticks=3,
        trailing_stop_pct=0.015,
        atr_stop_multiplier=2.0,
        partial_take_pct_trending=0.008,
        partial_take_pct_ranging=0.006,
        position_size_usd=10.0,
    )
    strategies.append(StrategyConfig("SNIPER", "Target", s2))
    
    # 3. VOL_MONSTER (New - Trend Accumulator)
    s3 = EngineConfig(
        arm_velocity_threshold=0.0060, # 0.6% High threshold
        arm_persistence_ticks=4,
        trailing_stop_pct=0.03,        # Wide 3% trail to survive volatility
        atr_stop_multiplier=3.0,
        partial_take_pct_trending=0.015, # 1.5% target
        partial_take_pct_ranging=0.010,
        position_size_usd=10.0,
    )
    strategies.append(StrategyConfig("VOL_MONSTER", "Trend", s3))

    # 4. RSI_DIP (New - Reversion)
    s4 = EngineConfig(
        rsi_entry_enabled=True,
        rsi_period=14,
        rsi_oversold=20,       # Deep oversold (was 25)
        rsi_overbought=80,     # Deep overbought (was 75)
        trailing_stop_pct=0.02, # Wider trail (2%)
        atr_stop_multiplier=2.0,
        partial_take_pct_trending=0.015,
        position_size_usd=10.0,
        cooldown_duration_seconds=300, # 5 Minute cooldown to prevent knife catching
        active_strategy="mean_reversion"
    )
    strategies.append(StrategyConfig("RSI_DIP", "Dip", s4))

    # 5. PUMP_HUNTER (New - Aggressive)
    s5 = EngineConfig(
        arm_velocity_threshold=0.012, # 1.2% Massive velocity required
        arm_persistence_ticks=2,
        trailing_stop_pct=0.005,      # Initial tight trail (lock in pump)
        atr_stop_multiplier=2.0,
        partial_take_pct_trending=0.02, # 2% target
        post_partial_trail_reduction=0.4, # Tighten massively after partial
        position_size_usd=10.0,
    )
    strategies.append(StrategyConfig("PUMP_HUNTER", "Pump", s5))

    # 6. OPTIMIZED (Baseline)
    s6 = EngineConfig(
        arm_velocity_threshold=0.008,
        arm_persistence_ticks=8,
        trailing_stop_pct=0.02,
        atr_stop_multiplier=2.5,
        partial_take_pct_trending=0.015,
        partial_take_pct_ranging=0.01,
        position_size_usd=10.0,
        loser_suppression_enabled=True,
        active_strategy="momentum"
    )
    strategies.append(StrategyConfig("OPTIMIZED", "Safe", s6))
    
    return strategies

    strategies.append(StrategyConfig("OPTIMIZED", "Safe", s6))
    
    return strategies

class QueueFeed:
    """Adapter to make a Queue look like a Feed."""
    def __init__(self, q: queue.Queue):
        self.q = q
        
    def get_next_tick(self):
        try:
            return self.q.get(timeout=5) # Wait up to 5s for data
        except queue.Empty:
            return None

class CentralMarketData:
    """
    Fetches ALL tickers in ONE API call and distributes to queues.
    Drastically reduces API limit consumption.
    """
    def __init__(self, symbols: List[str]):
        import ccxt
        self.symbols = symbols
        # Convert to exchange format (e.g. SUIUSDT -> SUI/USDT) for robust matching
        self.api_symbols = [s.replace("USDT", "/USDT") if "/" not in s else s for s in symbols]
        self.symbol_map = {api: orig for api, orig in zip(self.api_symbols, symbols)}
        
        self.queues = defaultdict(list)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.exchange = ccxt.binance({'enableRateLimit': True})
        
    def create_feed(self, symbol: str) -> QueueFeed:
        q = queue.Queue()
        self.queues[symbol].append(q)
        return QueueFeed(q)
        
    def start(self):
        self.thread.start()
        
    def stop(self):
        self.running = False
        
    def _run(self):
        from engine.market_data import Tick
        while self.running:
            try:
                # Fetch ALL tickers in one batch
                tickers = self.exchange.fetch_tickers(self.api_symbols)
                
                current_time = datetime.now(timezone.utc)
                
                for api_symbol, ticker_data in tickers.items():
                    # Map back to our internal symbol name
                    internal_symbol = self.symbol_map.get(api_symbol)
                    if not internal_symbol: 
                        # Try direct match just in case
                        if api_symbol in self.queues: internal_symbol = api_symbol
                        else: continue
                        
                    price = ticker_data['last']
                    volume = ticker_data.get('baseVolume', 0.0)
                    
                    tick = Tick(
                        timestamp=current_time,
                        price=price,
                        volume=volume
                    )
                    
                    # Distribute to all queues for this symbol
                    for q in self.queues[internal_symbol]:
                        q.put(tick)
                        
                time.sleep(1.0) # 1s Polling is safe for single batch request
                
            except Exception as e:
                with open("critical_feed_error.log", "a") as f:
                    f.write(f"{datetime.now()}: Feed Error: {e}\n")
                time.sleep(5) # Backoff
            
            # Debug log to verify execution frequency
            with open("debug_feed.log", "a") as f:
                f.write(f"{datetime.now()}: Fetched batch. Queues: {len(self.queues)}\n")

def run_strategy_engine(strategy: StrategyConfig, symbol: str, wallet: Wallet, stop_event: threading.Event, feed_provider):
    logger = EngineLogger(log_file=None, log_level="INFO")
    engine = TradingEngine(symbol=symbol, config=strategy.config, logger=logger)
    
    # Use the provided feed (QueueFeed) instead of creating a new LiveFeed
    feed = feed_provider
    last_pnl = 0.0
    
    while not stop_event.is_set():
        try:
            tick = feed.get_next_tick()
            if tick:
                engine.on_tick(tick)
                # Thread-safe update of current prices
                strategy.current_prices[symbol] = tick.price
                
                stats = engine.get_statistics()
                current_total_pnl = stats.get('total_pnl', 0.0)
                
                if current_total_pnl != last_pnl:
                    delta = current_total_pnl - last_pnl
                    wallet.update_pnl(delta)
                    last_pnl = current_total_pnl
                
                strategy.stats[symbol]['trades'] = stats.get('total_trades', 0)
                strategy.stats[symbol]['wins'] = stats.get('winning_trades', 0)
                strategy.stats[symbol]['losses'] = stats.get('losing_trades', 0)
                strategy.stats[symbol]['total_pnl'] = current_total_pnl
        except Exception as e:
            with open("engine_errors.log", "a") as f:
                f.write(f"{datetime.now()} {strategy.name} {symbol} CRITICAL ERROR: {e}\n")


def generate_dashboard(wallet: Wallet, strategies: List[StrategyConfig], symbols: List[str]) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body")
    )
    
    # Header
    bal = wallet.get_balance()
    pct = wallet.get_pnl_pct()
    color = "green" if pct >= 0 else "red"
    # 8 Decimal Precision
    header_text = f"💰 BALANCE: ${bal:.8f}  |  PnL: [{color}]{pct:+.4f}%[/{color}]  |  Started: $50.00000000"
    layout["header"].update(Panel(header_text, style=f"bold {color}", title="Portfolio Status"))
    
    # Table
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Symbol", style="cyan", width=9)
    table.add_column("Price", style="yellow", justify="right", width=12)
    
    for strategy in strategies:
        name_short = strategy.name[:4]
        table.add_column(f"{name_short}\nPnL", justify="center")
    
    for symbol in symbols:
        price = strategies[0].current_prices.get(symbol, 0.0)
        # 8 chars for price mostly
        price_str = f"{price:.8f}" if price > 0 else "..."
        row = [symbol, price_str]
        
        for strategy in strategies:
            pnl = strategy.stats[symbol]['total_pnl']
            # trades = strategy.stats[symbol]['trades']
            # Only show PnL to save space for 8dp
            pnl_str = f"{pnl:+.8f}"
            if pnl > 0: pnl_color = "green"
            elif pnl < 0: pnl_color = "red"
            else: pnl_color = "white"
            row.append(f"[{pnl_color}]{pnl_str}[/{pnl_color}]")
        table.add_row(*row)
        
    # Totals
    totals_row = ["[bold]TOTAL[/bold]", ""]
    for strategy in strategies:
        total_pnl = sum(s['total_pnl'] for s in strategy.stats.values())
        pnl_str = f"${total_pnl:+.8f}"
        if total_pnl > 0: pnl_color = "bold green"
        elif total_pnl < 0: pnl_color = "bold red"
        else: pnl_color = "bold"
        totals_row.append(f"[{pnl_color}]{pnl_str}[/{pnl_color}]")
        
    table.add_row(*totals_row, style="bold")
    
    layout["body"].update(Panel(table, title="Strategy Performance (8-Decimal Precision)", border_style="blue"))
    
    return layout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=0)
    parser.add_argument('--coins', type=int, default=15, choices=[5, 10, 15, 20])
    args = parser.parse_args()
    
    symbols = VOLATILE_COINS_15[:args.coins]
    strategies = create_strategies()
    wallet = Wallet(initial_balance=50.0)
    
    console.print("[yellow]Initializing High-Precision Volatility Hunter...[/yellow]")
    
    stop_event = threading.Event()
    
    # Initialize Central Feeder
    console.print(f"[cyan]Connecting to Binance (Batch Mode for {len(symbols)} coins)...[/cyan]")
    data_hub = CentralMarketData(symbols)
    data_hub.start()
    
    # Wait a moment for first data
    time.sleep(2.0)
        
    threads = []
    
    console.print("[yellow]Launching Strategies...[/yellow]")
    for strategy in strategies:
        for symbol in symbols:
            # Get a feed for this specific engine
            feed = data_hub.create_feed(symbol)
            
            t = threading.Thread(
                target=run_strategy_engine,
                args=(strategy, symbol, wallet, stop_event, feed),
                daemon=True
            )
            t.start()
            threads.append(t)
            
    start_time = time.time()
    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                live.update(generate_dashboard(wallet, strategies, symbols))
                if args.duration > 0 and time.time() - start_time >= args.duration: break
                time.sleep(1)
    except KeyboardInterrupt:
        pass
        
    stop_event.set()
    data_hub.stop()

    # Save Session Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "duration": args.duration,
        "initial_balance": wallet.initial_balance,
        "final_balance": wallet.get_balance(),
        "total_pnl_pct": wallet.get_pnl_pct(),
        "strategies": {},
        "wallet_history": wallet.history
    }

    for s in strategies:
        report["strategies"][s.name] = {
            "stats": s.stats
        }

    os.makedirs("results", exist_ok=True)
    report_path = "results/latest_live_session.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    console.print(f"\n[bold]Session Ended. Report saved to {report_path}[/bold]")
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
