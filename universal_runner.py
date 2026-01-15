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

# Setup Logging
logging.basicConfig(filename='universal_runner.log', level=logging.INFO, filemode='w')

# --- CONFIGURATION ---
# Coins extracted from user text and verified on Binance
TARGET_COINS = [
    'DOLO/USDT',
    'BTC/USDT', 
    'ETH/USDT', 
    'BNB/USDT', 
    'SOL/USDT', 
    'XRP/USDT', 
    'DOGE/USDT'
]

# Note: The following coins from text were NOT found on Binance:
# AIA, BOT, DAM, AIX, CC, GOATS, BFI, DDOYR, BBI, OMNIA, TTBK

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
console = Console()

# --- V1 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v1_legacy'))
try:
    from v1_legacy.trading_engine import SymbolData as V1SymbolData, RegimeDetector as V1Regime, TradeState as V1State
    v1_states = {}
    for coin in TARGET_COINS:
        v1_states[coin] = V1SymbolData(coin)
    logging.info("V1 Loaded")
except Exception as e:
    logging.error(f"Failed to import V1: {e}")
    V1SymbolData = None

# --- V2 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v2_modern'))
try:
    from src.engine import TradingEngine as V2Engine
    from src.config import DEFAULT_CONFIG as V2_CONFIG
    
    class DirectFeedV2:
        def __init__(self):
            self.current_tick = None
        def next(self):
            return self.current_tick
            
    # Initialize V2 (Placeholder as it requires complex feed setup)
    v2_engine = None # Skip deep integration for V2 in this quick runner
    logging.info("V2 Placeholder (Skipped)")
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
        clean_sym = coin.replace('/', '')
        cfg = V3Config(log_level="ERROR") 
        logger = V3Logger(log_file=f"logs/v3_{clean_sym}.log", log_level="ERROR") 
        v3_engines[coin] = V3Engine(clean_sym, cfg, logger)
    logging.info("V3 Loaded")
        
except Exception as e:
    logging.error(f"Failed to import V3: {e}")
    V3Engine = None

# --- V4 INTEGRATION ---
sys.path.append(os.path.join(APP_ROOT, 'v4'))
try:
    from v4.engine.engine import TradingEngine as V4Engine
    from v4.config.config import load_config as load_v4_config
    from v4.strategies.momentum import MomentumStrategy # Import real strategy
    
    v4_cfg = load_v4_config(os.path.join(APP_ROOT, 'v4/config.yaml'))
    v4_engines = {}
    
    for coin in TARGET_COINS:
        risk = getattr(v4_cfg, 'risk', {}) 
        # Create strategy instance
        strat_config = getattr(v4_cfg, 'strategy', {})
        strategy = MomentumStrategy("MOMENTUM_V4", strat_config)
        
        v4_engines[coin] = V4Engine(symbol=coin, strategy=strategy, risk_config=risk)
    logging.info("V4 Loaded")
    
except Exception as e:
    logging.error(f"Failed to import V4: {e}")
    # Fallback to mock if import fails
    try:
        class MockStrategy:
            def __init__(self): self.config = {}
            def generate_signals(self, tick): return []
            def on_fill(self, fill): pass
        
        v4_engines = {}
        for coin in TARGET_COINS:
            v4_engines[coin] = V4Engine(symbol=coin, strategy=MockStrategy(), risk_config={})
        logging.warning("V4 Loaded with MockStrategy due to import error")
    except:
        V4Engine = None

# --- MAIN RUNNER ---

async def run_universal():
    # 1. Init Exchange
    exchange = ccxt.binance()
    
    # 2. Results Storage
    results = {c: {'price': 0.0, 'v1': 'INIT', 'v2': 'n/a', 'v3': 'INIT', 'v4': 'INIT'} for c in TARGET_COINS}
    
    # 3. Helper to update V1
    def update_v1(coin, price):
        if not V1SymbolData: return "N/A"
        data = v1_states[coin]
        data.update_price(price)
        vel = data.get_velocity()
        
        # Manually run transition logic (simplified)
        if data.state == V1State.WAIT:
            if abs(vel) > 0.15: 
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
        class MockTick:
            def __init__(self, p, t):
                self.price = p
                self.timestamp = t
                self.symbol = clean_sym
        
        t = MockTick(price, datetime.now())
        eng.on_tick(t)
        return f"{eng.state_machine.state.name}"

    # 5. Helper to update V4
    async def update_v4(coin, price):
        if not V4Engine: return "N/A"
        if coin not in v4_engines: return "ERR"
        eng = v4_engines[coin]
        
        # Create a V4 tick if needed or just access engine methods
        # Engine execution usually happens via on_tick
        
        # We need a proper tick object. 
        # v4.common.types.Tick
        from v4.common.types import Tick
        tick = Tick(symbol=coin, price=price, timestamp=datetime.now(), volume=0)
        
        await eng.on_tick(tick) # CORRECTED from process_tick
        
        if hasattr(eng, 'state'):
            return str(eng.state)
        else:
            return "RUNNING" # Placeholder if state is hidden

    # --- LIVE LOOP ---
    with Live(refresh_per_second=4) as live:
        while True:
            # Fetch Data
            try:
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
                # results[coin]['v2'] = update_v2(coin, price)
                results[coin]['v3'] = update_v3(coin, price)
                try:
                    results[coin]['v4'] = await update_v4(coin, price)
                except Exception as ex:
                    logging.error(f"V4 Error: {ex}")
                    results[coin]['v4'] = "ERR"
                
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
