from typing import Optional, List, Any
from datetime import datetime
from collections import deque
import statistics

from ..strategy import Strategy, Signal
from ..market_data import Tick
from ..enums import SignalType

def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.
    """
    if len(prices) < period:
        return None
        
    multiplier = 2 / (period + 1)
    ema = prices[0] # Start with SMA or first price for approximation
    
    # Better: Start with simple average of first 'period' elements
    # But for streaming, we might just assume the list is long enough
    
    # Recalculate full EMA chain for correctness on every tick? 
    # For optimization, we should store state, but pure function is safer for now.
    
    # Implementation:
    # SMA for first 'period'
    sma = sum(prices[:period]) / period
    ema = sma
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
        
    return ema

class TrendFollowingStrategy(Strategy):
    """
    Trend Following Strategy.
    
    Logic:
    EMA Crossover (Golden/Death Cross)
    
    Entry Long: Fast EMA > Slow EMA (Golden Cross)
    Entry Short: Fast EMA < Slow EMA (Death Cross)
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.name = "TrendFollowingStrategy"
        
        self.fast_period = getattr(config, 'fast_ema', 50)
        self.slow_period = getattr(config, 'slow_ema', 200)
        
        # State - needs a lot of history
        self.prices = deque(maxlen=self.slow_period * 2)
        
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        self.prices.append(tick.price)
        prices_list = list(self.prices)
        
        if len(prices_list) < self.slow_period + 10:
            return None
            
        fast_ema = calculate_ema(prices_list, self.fast_period)
        slow_ema = calculate_ema(prices_list, self.slow_period)
        
        if fast_ema is None or slow_ema is None:
            return None
            
        # Check Crossover
        # Ideally we check if it JUST crossed, requiring previous EMAs.
        # For simplicity here: State-based (if condition met, signal).
        # To prevent spamming signals, the Engine/RiskManager filters duplicates.
        
        if fast_ema > slow_ema and tick.price > fast_ema:
             return Signal(
                type=SignalType.LONG,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Golden Cross: {fast_ema:.2f} > {slow_ema:.2f}"
            )
            
        if fast_ema < slow_ema and tick.price < fast_ema:
             return Signal(
                type=SignalType.SHORT,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Death Cross: {fast_ema:.2f} < {slow_ema:.2f}"
            )
            
        return None
