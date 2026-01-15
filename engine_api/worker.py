import sys
import os
import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from .models import EngineStatus, EngineInsights, InsightV1, InsightV2, InsightV3, InsightV4
from .store import EngineStateStore

# --- Path Setup ---
# Assuming this file is at root/engine_api/worker.py
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- API Mocks & Helpers ---
class MockV2Feed:
    """Minimal feed for V2 engine."""
    def __init__(self):
        self._current_time = datetime.now().timestamp()
    def now(self):
        return self._current_time
    def get_tickers(self, symbols):
        return {}

# --- Worker Class ---
class EngineWorker:
    def __init__(self, symbol: str, store: EngineStateStore, executor: ThreadPoolExecutor):
        self.symbol = symbol
        self.store = store
        self.executor = executor
        self.status = EngineStatus.STOPPED
        self.queue = asyncio.Queue()  # Receives price updates
        
        # Engine State Containers
        self.v1_data = None
        self.v2_engine = None
        self.v3_engine = None
        self.v4_engine = None
        
        self.v1_cls = None
        self.v3_cls = None
        
    async def start(self):
        """Lifecycle: STARTING -> RUNNING -> (Loop) -> STOPPED/ERROR"""
        if self.status == EngineStatus.RUNNING:
            return

        try:
            logging.info(f"[{self.symbol}] Worker Starting...")
            self.status = EngineStatus.STARTING
            self.store.write_status(self.symbol, EngineStatus.STARTING)
            
            # Offload heavy initialization to executor
            await asyncio.get_running_loop().run_in_executor(self.executor, self._init_engines)
            
            self.status = EngineStatus.RUNNING
            self.store.write_status(self.symbol, EngineStatus.RUNNING)
            logging.info(f"[{self.symbol}] Worker Running")
            
            await self._run_loop()
            
        except Exception as e:
            logging.error(f"[{self.symbol}] Startup Failed: {e}", exc_info=True)
            self.status = EngineStatus.ERROR
            self.store.write_status(self.symbol, EngineStatus.ERROR, str(e))

    def _init_engines(self):
        """Synchronous initialization of all engines."""
        # 1. V1 Legacy
        sys.path.append(os.path.join(APP_ROOT, 'v1_legacy'))
        from v1_legacy.trading_engine import SymbolData as V1SymbolData, TradeState as V1State
        self.v1_data = V1SymbolData(self.symbol)
        self.v1_cls = V1State # Save ref to Enum

        # 2. V2 Modern
        sys.path.append(os.path.join(APP_ROOT, 'v2_modern'))
        from src.engine import TradingEngine as V2Engine
        from src.config import DEFAULT_CONFIG as V2_CONFIG
        # Initialize with single symbol support
        self.v2_engine = V2Engine(V2_CONFIG, MockV2Feed(), symbols=[self.symbol])

        # 3. V3 Strict
        sys.path.append(os.path.join(APP_ROOT, 'v3'))
        from v3.engine.engine import TradingEngine as V3Engine
        from v3.engine.config import EngineConfig as V3Config
        from v3.engine.logger import EngineLogger as V3Logger
        
        clean_sym = self.symbol.replace('/', '')
        cfg = V3Config(log_level="ERROR")
        logger = V3Logger(log_file=f"logs/v3_{clean_sym}_api.log", log_level="ERROR")
        self.v3_engine = V3Engine(clean_sym, cfg, logger)

        # 4. V4 Async (Import only, instantiated here but run in async loop normally)
        sys.path.append(os.path.join(APP_ROOT, 'v4'))
        from v4.engine.engine import TradingEngine as V4Engine
        from v4.config.config import load_config as load_v4_config
        # Use Mock strategy for safety/speed if real one has issues, 
        # but let's try Real Momentum first as per Universal Runner
        from v4.strategies.momentum import MomentumStrategy
        
        v4_cfg = load_v4_config(os.path.join(APP_ROOT, 'v4/config.yaml'))
        strategy = MomentumStrategy("MOMENTUM_V4", getattr(v4_cfg, 'strategy', {}))
        self.v4_engine = V4Engine(symbol=self.symbol, strategy=strategy, risk_config=getattr(v4_cfg, 'risk', {}))

    async def _run_loop(self):
        """Main processing loop."""
        while self.status == EngineStatus.RUNNING:
            try:
                # Wait for price tick (with timeout to check status)
                try:
                    price = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Update Timestamp
                now = datetime.now()
                
                # 1. Run CPU-bound sync engines in ThreadPool
                v1_res, v2_res, v3_res = await asyncio.get_running_loop().run_in_executor(
                    self.executor, self._update_sync_engines, price, now
                )
                
                # 2. Run IO-bound/native async V4
                v4_res = await self._update_v4(price, now)
                
                # 3. Compile & Publish
                insights = EngineInsights(
                    symbol=self.symbol,
                    timestamp=now,
                    price=price,
                    v1=v1_res,
                    v2=v2_res,
                    v3=v3_res,
                    v4=v4_res
                )
                
                self.store.write_insights(self.symbol, insights)

            except asyncio.CancelledError:
                self.status = EngineStatus.STOPPED
                break
            except Exception as e:
                logging.error(f"[{self.symbol}] Loop Error: {e}")
                self.status = EngineStatus.ERROR
                self.store.write_status(self.symbol, EngineStatus.ERROR, str(e))
                break

    def _update_sync_engines(self, price: float, now: datetime):
        """Run v1, v2, v3 in separate thread."""
        # --- V1 ---
        v1_out = None
        try:
            self.v1_data.update_price(price)
            vel = self.v1_data.get_velocity()
            # Minimal State Machine Replicating Universal Runner
            if self.v1_data.state == self.v1_cls.WAIT:
                if abs(vel) > 0.15: self.v1_data.state = self.v1_cls.ARM
            elif self.v1_data.state == self.v1_cls.ARM:
                if abs(vel) > 0.15: 
                    self.v1_data.arm_streak += 1
                    if self.v1_data.arm_streak > 3: self.v1_data.state = self.v1_cls.ENTRY
                else: self.v1_data.state = self.v1_cls.WAIT
            
            v1_out = InsightV1(
                state=self.v1_data.state.name,
                velocity=round(vel, 4),
                trend="UP" if vel > 0 else "DOWN"
            )
        except Exception as e:
            logging.warning(f"V1 Fail: {e}")

        # --- V2 ---
        v2_out = None
        try:
            # Manually inject tick into V2
            # V2 expects ticker dict
            ticker = {
                'symbol': self.symbol,
                'last': price,
                'timestamp': now.timestamp()
            }
            # Hack: Manually update feed time so now() works inside engine
            self.v2_engine.market_feed._current_time = now.timestamp()
            self.v2_engine._process_symbol(self.symbol, ticker, now.timestamp(), now.isoformat())
            
            sym_data = self.v2_engine.symbol_data[self.symbol]
            v2_out = InsightV2(
                signal=sym_data.state.name, # Use State as Signal proxy
                confidence=0.0 # V2 doesn't expose confidence directly
            )
        except Exception as e:
            logging.warning(f"V2 Fail: {e}")

        # --- V3 ---
        v3_out = None
        try:
            clean_sym = self.symbol.replace('/', '')
            class MockTick:
                def __init__(self, p, t, s):
                    self.price = p; self.timestamp = t; self.symbol = s
            
            t = MockTick(price, now, clean_sym)
            self.v3_engine.on_tick(t)
            
            # Derive trend from recent price movement via V1 velocity
            trend = "FLAT"
            if hasattr(self.v1_data, 'get_velocity'):
                vel = self.v1_data.get_velocity()
                if vel > 0.05:
                    trend = "UP"
                elif vel < -0.05:
                    trend = "DOWN"
            
            v3_out = InsightV3(
                state=self.v3_engine.state_machine.state.name,
                regime="UNKNOWN",  # V3 logic is complex for regime exposure
                active_strategy="Momentum",
                trend=trend
            )
        except Exception as e:
            logging.warning(f"V3 Fail: {e}")

        return v1_out, v2_out, v3_out

    async def _update_v4(self, price: float, now: datetime):
        """Run V4 async with real engine state extraction."""
        try:
            from v4.common.types import Tick
            tick = Tick(symbol=self.symbol, price=price, timestamp=now, volume=0)
            await self.v4_engine.on_tick(tick)
            
            # Extract real data from engine state
            signal = "RUNNING"
            pnl = None
            risk_score = 0.5
            
            # Try to get actual position and PnL
            if hasattr(self.v4_engine, 'position') and self.v4_engine.position:
                position = self.v4_engine.position
                if hasattr(position, 'unrealized_pnl'):
                    pnl = float(position.unrealized_pnl)
                if hasattr(position, 'side'):
                    signal = position.side  # LONG/SHORT
            
            # Try to get state information
            if hasattr(self.v4_engine, 'state'):
                signal = self.v4_engine.state.name if hasattr(self.v4_engine.state, 'name') else str(self.v4_engine.state)
            
            return InsightV4(
                signal=signal,
                risk_score=risk_score,
                pnl_projected=pnl
            )
        except Exception as e:
            logging.warning(f"V4 Fail: {e}")
            return None

    async def stop(self):
        self.status = EngineStatus.STOPPED
        self.store.write_status(self.symbol, EngineStatus.STOPPED)
