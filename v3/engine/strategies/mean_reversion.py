from typing import Optional, List, Any
from datetime import datetime
from collections import deque
import statistics

from ..strategy import Strategy, Signal
from ..market_data import Tick
from ..enums import SignalType
from .. import indicators

class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy (Crypto-Optimized).
    
    Logic:
    1. Bollinger Bands (20, 2.0)
    2. RSI (14)
    
    Entry Long: Close < Lower Band AND RSI < 30
    Entry Short: Close > Upper Band AND RSI > 70
    Exit: Revert to Mean (Middle Band) or Stop Loss
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.name = "MeanReversionStrategy"
        
        # Parameters
        self.bb_period = getattr(config, 'bb_period', 20)
        self.bb_std = getattr(config, 'bb_std', 2.0)
        self.rsi_period = getattr(config, 'rsi_period', 14)
        
        # State
        self.prices = deque(maxlen=max(self.bb_period, self.rsi_period) + 10)
        
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        self.prices.append(tick.price)
        
        if len(self.prices) < self.bb_period:
            return None
            
        prices_list = list(self.prices)
        
        # Calculate Bollinger Bands
        sma = statistics.mean(prices_list[-self.bb_period:])
        stdev = statistics.stdev(prices_list[-self.bb_period:])
        upper_band = sma + (self.bb_std * stdev)
        lower_band = sma - (self.bb_std * stdev)
        
        # Calculate RSI
        rsi = indicators.calculate_rsi(prices_list, self.rsi_period)
        if rsi is None:
            return None
            
        current_price = tick.price
        
        # Entry Logic
        if current_price < lower_band and rsi < 30:
            return Signal(
                type=SignalType.LONG,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=current_price,
                reason=f"BB Low: {lower_band:.2f} | RSI: {rsi:.1f}"
            )
            
        if current_price > upper_band and rsi > 70:
            return Signal(
                type=SignalType.SHORT,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=current_price,
                reason=f"BB High: {upper_band:.2f} | RSI: {rsi:.1f}"
            )
            
        return None
