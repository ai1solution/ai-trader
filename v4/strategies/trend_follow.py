"""
Trend Following Strategy.
EMA Cross.
"""
from collections import deque
from typing import List, Dict
import pandas as pd
from .interface import Strategy, Intent, FillEvent, Tick, OrderSide

class TrendFollowingStrategy(Strategy):
    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.fast_period = config.get('ema_fast', 9)
        self.slow_period = config.get('ema_slow', 21)
        
        self.prices = deque(maxlen=self.slow_period + 10)
        
    def generate_signals(self, tick: Tick) -> List[Intent]:
        self.prices.append(tick.price)
        
        if len(self.prices) < self.slow_period:
            return []
            
        prices_series = pd.Series(list(self.prices))
        
        ema_fast = prices_series.ewm(span=self.fast_period, adjust=False).mean().iloc[-1]
        ema_slow = prices_series.ewm(span=self.slow_period, adjust=False).mean().iloc[-1]
        
        # Check previous values for crossover
        prev_fast = prices_series.ewm(span=self.fast_period, adjust=False).mean().iloc[-2]
        prev_slow = prices_series.ewm(span=self.slow_period, adjust=False).mean().iloc[-2]
        
        # Golden Cross (Fast crosses above Slow)
        if prev_fast <= prev_slow and ema_fast > ema_slow:
             return [Intent(self.name, tick.symbol, OrderSide.BUY, 0.0, reason="Golden_Cross")]
             
        # Death Cross (Fast crosses below Slow)
        if prev_fast >= prev_slow and ema_fast < ema_slow:
             return [Intent(self.name, tick.symbol, OrderSide.SELL, 0.0, reason="Death_Cross")]
             
        return []

    def on_fill(self, fill: FillEvent):
        pass

    def on_bar_close(self, bar):
        pass
