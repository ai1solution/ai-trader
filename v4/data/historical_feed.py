"""
Historical Data Feed for Replay.
"""
import pandas as pd
import asyncio
from typing import Optional, List, Deque
from collections import deque
from datetime import datetime, timedelta, timezone

from ..common.interfaces import MarketDataFeed
from ..common.types import Tick, Candle
from .ccxt_provider import CCXTProvider
from .caching import load_cached_ohlcv, save_to_cache

class HistoricalFeed(MarketDataFeed):
    """
    Feeds 1-minute candles as interpolated ticks.
    """
    def __init__(self, symbol: str, start: datetime, end: datetime, 
                 interval_seconds: float = 2.0, use_cache: bool = True):
        self.symbol = symbol
        self.start_time = start
        self.end_time = end
        self.interval_seconds = interval_seconds
        
        self.ticks: Deque[Tick] = deque()
        self.current_time = start
        self.data_loaded = False
        self._provider = CCXTProvider() # Default provider
        
    async def initialize(self):
        """
        Fetch data and generate ticks.
        This must be called before usage.
        """
        print(f"[HistoricalFeed] Initializing {self.symbol}...")
        
        # 1. Try Cache
        start_str = self.start_time.strftime("%Y%m%d%H%M")
        end_str = self.end_time.strftime("%Y%m%d%H%M")
        
        df = load_cached_ohlcv(self.symbol, start_str, end_str)
        
        # 2. Fetch if missing
        if df is None or df.empty:
            df = await self._provider.fetch_ohlcv(
                self.symbol, '1m', self.start_time, self.end_time
            )
            if not df.empty:
                save_to_cache(df, self.symbol, start_str, end_str)
        
        if df is None or df.empty:
            print(f"[HistoricalFeed] No data found for {self.symbol}")
            return

        # 3. Generate Ticks (Interpolation)
        self._generate_ticks(df)
        self.data_loaded = True
        
        first_ts = self.ticks[0].timestamp if self.ticks else "None"
        last_ts = self.ticks[-1].timestamp if self.ticks else "None"
        print(f"[HistoricalFeed] {self.symbol} Ready: {len(self.ticks)} ticks. Range: {first_ts} to {last_ts}")
        
    def _generate_ticks(self, df: pd.DataFrame):
        """
        Convert OHLCV candles to ticks.
        """
        ticks_per_candle = int(60 / self.interval_seconds)
        tick_delta = timedelta(seconds=self.interval_seconds)
        
        for idx, row in df.iterrows():
            ts = row['timestamp']
            row_o, row_h, row_l, row_c = row['open'], row['high'], row['low'], row['close']
            vol = row['volume'] / ticks_per_candle
            
            # Phases: O->H (25%), H->L (25%), L->C (50%)
            n = ticks_per_candle
            p1 = max(1, n // 4)
            p2 = max(1, n // 4)
            p3 = n - p1 - p2
            
            # Phase 1: O -> H
            for i in range(p1):
                progress = i / p1
                price = row_o + (row_h - row_o) * progress
                self.ticks.append(Tick(ts + (tick_delta * i), price, vol, self.symbol))
                
            # Phase 2: H -> L
            base_ts = ts + (tick_delta * p1)
            for i in range(p2):
                progress = i / p2
                price = row_h + (row_l - row_h) * progress
                self.ticks.append(Tick(base_ts + (tick_delta * i), price, vol, self.symbol))
                
            # Phase 3: L -> C
            base_ts = ts + (tick_delta * (p1 + p2))
            for i in range(p3):
                progress = (i + 1) / p3
                price = row_l + (row_c - row_l) * progress
                is_close = (i == p3 - 1)
                self.ticks.append(Tick(base_ts + (tick_delta * i), price, vol, self.symbol, is_candle_close=is_close))

    def get_ticks(self) -> List[Tick]:
        """
        Return a list of all ticks (without consuming them).
        Useful for optimization/training where data is shared.
        """
        return list(self.ticks)

    async def get_next_tick(self) -> Optional[Tick]:
        if not self.ticks:
            return None
        
        tick = self.ticks.popleft()
        self.current_time = tick.timestamp
        return tick
        
    def get_current_time(self) -> datetime:
        return self.current_time
        
    async def cleanup(self):
        await self._provider.cleanup()
