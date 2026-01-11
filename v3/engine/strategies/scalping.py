from typing import Optional, List, Any
from datetime import datetime
from collections import deque
import statistics

from ..strategy import Strategy, Signal
from ..market_data import Tick
from ..enums import SignalType
from .. import indicators

class ScalpingStrategy(Strategy):
    """
    Scalping Variant (High Frequency).
    
    Logic:
    Very short-term momentum on high-liquidity pairs.
    Target: 0.1% - 0.5%
    Stop: Tighter than Swing.
    
    Entry: High instantaneous velocity burst.
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.name = "ScalpingStrategy"
        
        # Tighter parameters
        self.lookback = getattr(config, 'scalp_lookback', 5) # Very short
        self.threshold = getattr(config, 'scalp_threshold', 0.0005) # 0.05% burst
        
        self.prices = deque(maxlen=self.lookback + 5)
        
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        self.prices.append(tick.price)
        
        velocity = indicators.calculate_velocity(list(self.prices), self.lookback)
        if velocity is None:
            return None
            
        if velocity > self.threshold:
            return Signal(
                type=SignalType.LONG,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Scalp Burst: {velocity:.5f}",
                # Tighter stops for scalp
                stop_loss=tick.price * 0.995, # 0.5% stop
                take_profit=tick.price * 1.005 # 0.5% target
            )
            
        if velocity < -self.threshold:
             return Signal(
                type=SignalType.SHORT,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Scalp Dump: {velocity:.5f}",
                stop_loss=tick.price * 1.005,
                take_profit=tick.price * 0.995
            )
            
        return None
