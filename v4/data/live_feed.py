"""
Live Data Feed.
Ideally would use WebSockets. For now, implements polling via CCXTProvider.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from ..common.interfaces import MarketDataFeed
from ..common.types import Tick
from .ccxt_provider import CCXTProvider

class LiveFeed(MarketDataFeed):
    def __init__(self, symbol: str, interval_seconds: float = 2.0):
        self.symbol = symbol
        self.interval = interval_seconds
        self._provider = CCXTProvider()
        self._running = True
        self._last_tick_time = 0
        
    async def get_next_tick(self) -> Optional[Tick]:
        """
        Polls for ticker data. 
        Waits if called too frequently.
        """
        if not self._running:
            return None
            
        # Rate limiting
        now = datetime.now(timezone.utc).timestamp()
        elapsed = now - self._last_tick_time
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
            
        tick = await self._provider.fetch_ticker(self.symbol)
        if tick:
            self._last_tick_time = datetime.now(timezone.utc).timestamp()
            tick.is_candle_close = False # Live ticks are rarely exact closes unless calculated
            return tick
            
        return None
        
    def get_current_time(self) -> datetime:
        return datetime.now(timezone.utc)
        
    async def cleanup(self):
        self._running = False
        await self._provider.cleanup()
