from typing import Optional, List, Any
from datetime import datetime
from collections import deque
import statistics

from ..strategy import Strategy, Signal
from ..market_data import Tick
from ..enums import SignalType

class BreakoutStrategy(Strategy):
    """
    Breakout Strategy.
    
    Logic:
    1. Identify Range (High - Low over period)
    2. Entry if price breaks range High/Low
    3. Volume confirmation (optional)
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.name = "BreakoutStrategy"
        
        self.lookback = getattr(config, 'breakout_lookback', 50)
        self.volume_mult = getattr(config, 'volume_multiplier', 1.5)
        
        self.prices = deque(maxlen=self.lookback + 1)
        # self.volumes = deque(maxlen=self.lookback) # Todo: Tick doesn't have volume usually?
        
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        self.prices.append(tick.price)
        
        if len(self.prices) < self.lookback:
            return None
            
        # Recent High/Low (excluding current tick)
        recent_prices = list(self.prices)[:-1]
        range_high = max(recent_prices)
        range_low = min(recent_prices)
        
        # Breakout Check
        if tick.price > range_high:
            # Check volume if available (Mocking for now)
            return Signal(
                type=SignalType.LONG,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Breakout High: {tick.price} > {range_high}"
            )
            
        if tick.price < range_low:
             return Signal(
                type=SignalType.SHORT,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Breakout Low: {tick.price} < {range_low}"
            )
            
        return None
