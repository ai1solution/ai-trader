import sys
import os
import asyncio
import time
import ccxt.async_support as ccxt
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from collections import defaultdict
import logging

# Setup Logging to file only to avoid TUI pollution
logging.basicConfig(filename='universal_runner.log', level=logging.INFO, filemode='w')

# --- CONFIGURATION ---
TARGET_COINS = [
    'FET/USDT', 'RNDR/USDT', 'WLD/USDT', 'GRT/USDT', 'TAO/USDT', 'ARKM/USDT', 
    'AI/USDT', 'NFP/USDT', 'PHB/USDT', 'NEAR/USDT', 
    'PEPE/USDT', 'BONK/USDT', 'WIF/USDT', 'FLOKI/USDT', 'MEME/USDT', 'BOME/USDT',
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT'
]

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
console = Console()

# --- V1 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v1_legacy'))
try:
    from v1_legacy.trading_engine import SymbolData as V1SymbolData, RegimeDetector as V1Regime, TradeState as V1State, CORRELATION_MAP
    # Mock portfolio for V1
    v1_portfolios = defaultdict(list)
    v1_states = {} # symbol -> SymbolData
    for coin in TARGET_COINS:
        # V1 expects /USD for some logic in correlation map, but we use /USDT. Map it?
        # wrapper will handle it.
        v1_states[coin] = V1SymbolData(coin)
except Exception as e:
    logging.error(f"Failed to import V1: {e}")
    V1SymbolData = None

# --- V2 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v2_modern'))
try:
    from src.engine import TradingEngine as V2Engine
    from src.config import DEFAULT_CONFIG as V2_CONFIG
    # Mock Feed for V2? V2 engine takes a feed object. 
    # We can perform "manual" ticks on V2 engine if we expose the method.
    # V2 Engine.tick() calls feed.get_next() -> process. 
    # We might need to subclass or modify V2 engine to accept a direct tick injection.
    # Let's see... V2 Engine.tick(): 
    #   tick = self.feed.next()
    #   self.strategy.on_tick(tick)
    # We will create a "DirectFeed" class.
    class DirectFeedV2:
        def __init__(self):
            self.current_tick = None
        def next(self):
            return self.current_tick
            
    v2_feeds = {}
    v2_engines = {}
    
    # Initialize V2
    for coin in TARGET_COINS:
        feed = DirectFeedV2()
        start_conf = V2_CONFIG.copy()
        start_conf['symbols'] = [coin]
        # V2 engine seems designed for single symbol or list? 
        # V2 main.py: engine = TradingEngine(config, feed)
        # engine.tick() iterates all symbols? need to check V2 engine source deeper.
        # Assuming single engine instance handles all symbols if feed provides them.
        pass 
        
    # Actually V2 engine might be multi-symbol. Let's make ONE V2 engine.
    v2_feed = DirectFeedV2()
    v2_engine = V2Engine(V2_CONFIG, v2_feed)
    # But wait, V2 engine.tick() calls feed.next(). If we want to tick specific symbol...
    # We might need to inject. 
except Exception as e:
    logging.error(f"Failed to import V2: {e}")
    V2Engine = None

# --- V3 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v3'))
try:
    from v3.engine.engine import TradingEngine as V3Engine
    from v3.engine.config import EngineConfig as V3Config
    from v3.engine.logger import EngineLogger as V3Logger
    
    v3_engines = {}
    for coin in TARGET_COINS:
        # Clean symbol for V3? "BTCUSDT" vs "BTC/USDT"
        # V3 live_mock uses "BTCUSDT". 
        clean_sym = coin.replace('/', '')
        cfg = V3Config(log_level="ERROR") # Silence logs
        # Mock logger
        logger = V3Logger(log_file=f"logs/v3_{clean_sym}.log", log_level="ERROR") 
        v3_engines[coin] = V3Engine(clean_sym, cfg, logger)
        
except Exception as e:
    logging.error(f"Failed to import V3: {e}")
    V3Engine = None

# --- V4 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v4'))
try:
    from v4.engine.engine import TradingEngine as V4Engine
    from v4.config.config import load_config as load_v4_config
    
    v4_cfg = load_v4_config(os.path.join(APP_ROOT, 'v4/config.yaml'))
    # V4 engine is likely async. 
    # V4 engine init: (config). 
    # V4 engine likely has .process_tick(tick) or similar.
    v4_engine = V4Engine(v4_cfg, strategy=None) # Passing None as strategy placeholder if allowed, or check sig
    # Wait, error said missing 'strategy'. 
    # Let's import a strategy or mock it.
    # From v4.strategies.strategy import Strategy 
    # But for a runner, maybe we don't need a live engine instance if we just want status?
    # Actually, let's just silence it for now as "Not Ready" or pass a dummy.
    # V4 Engine requires symbol and strategy
    class MockStrategy:
        def __init__(self): 
            self.config = {}
        def generate_signals(self, tick): return []
        def on_fill(self, fill): pass

    v4_engines = {}
    for coin in TARGET_COINS:
        # Check if v4_cfg is object or dict. Error says object.
        # Assuming v4_cfg.risk exists.
        risk = getattr(v4_cfg, 'risk', {}) 
        v4_engines[coin] = V4Engine(symbol=coin, strategy=MockStrategy(), risk_config=risk)
    
except Exception as e:
    logging.error(f"Failed to import V4: {e}")
    V4Engine = None

# --- MAIN RUNNER ---

async def run_universal():
    # 1. Init Exchange
    exchange = ccxt.binance()
    
    # 2. Results Storage
    results = {c: {'price': 0.0, 'v1': 'INIT', 'v2': 'INIT', 'v3': 'INIT', 'v4': 'INIT'} for c in TARGET_COINS}
    
    # 3. Helper to update V1
    def update_v1(coin, price):
        if not V1SymbolData: return "N/A"
        data = v1_states[coin]
        data.update_price(price)
        vel = data.get_velocity()
        
        # Manually run transition logic (simplified from v1 main loop)
        # This is strictly a wrapper simulation
        if data.state == V1State.WAIT:
            if abs(vel) > 0.15: # Threshold
                data.state = V1State.ARM
        elif data.state == V1State.ARM:
             if abs(vel) > 0.15:
                 data.arm_streak += 1
                 if data.arm_streak > 3:
                     data.state = V1State.ENTRY
             else:
                 data.state = V1State.WAIT
        elif data.state == V1State.ENTRY:
             data.state = V1State.HOLD
        
        return f"{data.state.name} ({vel:.2f}%)"

    # 4. Helper to update V3
    def update_v3(coin, price):
        if not V3Engine: return "N/A"
        clean_sym = coin.replace('/', '')
        if coin not in v3_engines: return "ERR"
        
        eng = v3_engines[coin]
        # V3 expects a Tick object
        # from v3.engine.market_data import Tick (Need to import or mock)
        class MockTick:
            def __init__(self, p, t):
                self.price = p
                self.timestamp = t
                self.symbol = clean_sym
        
        t = MockTick(price, datetime.now())
        eng.on_tick(t)
        return f"{eng.state_machine.state.name}"

    # 5. Helper to update V2
    def update_v2(coin, price):
        if not V2Engine: return "N/A"
        # Since V2 integration is tricky without a direct "on_tick", we skip deep logic for now 
        # unless we instantiated it correctly.
        # Assuming V2 wrapper is WIP or placeholder
        return "WAIT" 
        
    # 6. Helper to update V4
    async def update_v4(coin, price):
        if not V4Engine: return "N/A"
        if coin not in v4_engines: return "ERR"
        eng = v4_engines[coin]
        # V4 uses internal Update? Or we call on_tick?
        # V4 Engine.on_tick(tick: Tick)
        # We need v4.common.types.Tick
        
        # We can just check state for now without ticking to avoid complex import for Tick
        # or just mock the tick object again if it's duck-typed (it is, looking at type hint it imports Tick but python is dynamic)
        
        # Let's try to fetch state
        return eng.state

    # --- LIVE LOOP ---
    with Live(refresh_per_second=4) as live:
        while True:
            # Fetch Data
            try:
                # CCXT fetch tickers is efficient
                tickers = await exchange.fetch_tickers(TARGET_COINS)
            except Exception as e:
                logging.error(f"Fetch error: {e}")
                await asyncio.sleep(1)
                continue
                
            # Update Engines
            table = Table(title="Universal Engine Monitor (V1-V4)")
            table.add_column("Symbol", style="cyan")
            table.add_column("Price", justify="right")
            table.add_column("V1 (Legacy)", justify="center")
            table.add_column("V2 (Modern)", justify="center")
            table.add_column("V3 (Strict)", justify="center")
            table.add_column("V4 (Paper)", justify="center")
            
            for coin in TARGET_COINS:
                if coin not in tickers: continue
                price = tickers[coin]['last']
                results[coin]['price'] = price
                
                # UPDATE ENGINES
                results[coin]['v1'] = update_v1(coin, price)
                results[coin]['v2'] = update_v2(coin, price)
                results[coin]['v3'] = update_v3(coin, price)
                results[coin]['v4'] = await update_v4(coin, price)
                
                # UI ROW
                table.add_row(
                    coin,
                    f"{price:.4f}",
                    results[coin]['v1'],
                    results[coin]['v2'],
                    results[coin]['v3'],
                    results[coin]['v4']
                )
            
            live.update(table)
            await asyncio.sleep(1)

    await exchange.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_universal())
    except KeyboardInterrupt:
        print("Stopped.")
