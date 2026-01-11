"""
Breakout Strategy.
Donchian Channels (High/Low of last N periods).
"""
from collections import deque
from typing import List, Dict
from .interface import Strategy, Intent, FillEvent, Tick, OrderSide

class BreakoutStrategy(Strategy):
    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.period = config.get('breakout_period', 20)
        self.prices = deque(maxlen=self.period + 1)
        
    def generate_signals(self, tick: Tick) -> List[Intent]:
        # Logic: 
        # If Price > Max(Last N), Buy.
        # If Price < Min(Last N), Sell.
        
        if len(self.prices) < self.period:
             self.prices.append(tick.price)
             return []
        
        # Calculate High/Low of PREVIOUS N ticks (excluding current)
        recent = list(self.prices)
        highest = max(recent)
        lowest = min(recent)
        
        self.prices.append(tick.price)
        
        if tick.price > highest:
             return [Intent(self.name, tick.symbol, OrderSide.BUY, 0.0, reason=f"Breakout_High_{highest}")]
        
        if tick.price < lowest:
             return [Intent(self.name, tick.symbol, OrderSide.SELL, 0.0, reason=f"Breakout_Low_{lowest}")]
             
        return []

    def on_fill(self, fill: FillEvent):
        pass

    def on_bar_close(self, bar):
        pass
