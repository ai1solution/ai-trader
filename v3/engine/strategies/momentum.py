from typing import Optional, List, Any
from datetime import datetime
from collections import deque
import statistics

from ..strategy import Strategy, Signal
from ..market_data import Tick
from ..enums import SignalType, Regime
from .. import indicators

class MomentumStrategy(Strategy):
    """
    Dynamic Volatility Hunter (v3 Port).
    
    Logic:
    1. Calculate Velocity (Tick-based momentum)
    2. Check Acceleration (Median velocity increasing)
    3. Setup Phase (ARM): Must maintain valid velocity/acceleration for N ticks
    4. Regime Filter: Long-only in strong uptrends, or volatility based
    5. RSI Filter: No longs if overbought
    """
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.name = "MomentumStrategy"
        
        # State
        self.velocities = deque(maxlen=50)
        self.prices = deque(maxlen=50) # Need history for regime/RSI
        self.arm_persistence_count = 0
        self.in_cooldown = False
        
        # Parameters (from config or defaults)
        self.lookback = getattr(config, 'lookback', 12)  # Tick lookback for velocity
        self.threshold = getattr(config, 'velocity_threshold', 0.0003)
        self.arm_ticks = getattr(config, 'arm_ticks', 3)
        self.rsi_period = getattr(config, 'rsi_period', 14)
        
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        self.prices.append(tick.price)
        
        # 1. Calculate Velocity
        velocity = indicators.calculate_velocity(list(self.prices), self.lookback)
        if velocity is None:
            return None
            
        self.velocities.append(velocity)
        
        # 2. Check Acceleration
        is_accelerating = indicators.calculate_velocity_acceleration(list(self.velocities))
        
        # 3. Calculate Regime & RSI
        # Use tick prices as proxy for High/Low/Close since we are tick-based
        prices_list = list(self.prices)
        atr = indicators.calculate_atr(prices_list, prices_list, prices_list, 14)
        
        regime = indicators.detect_regime(prices_list, atr, lookback=20)
        
        # Log context occasionally or debug (optional)
        # self.latest_regime = regime
        
        rsi = indicators.calculate_rsi(list(self.prices), self.rsi_period)
        
        # 4. Entry Logic (ARM -> SIGNAL)
        
        # Check Long Condition
        is_long_candidate = (
            velocity > self.threshold and
            is_accelerating and
            (rsi is None or rsi < 70)
        )
        
        # Check Short Condition
        is_short_candidate = (
            velocity < -self.threshold and
            is_accelerating and
            (rsi is None or rsi > 30)
        )
        
        # ARM Persistence
        if is_long_candidate or is_short_candidate:
            self.arm_persistence_count += 1
        else:
            self.arm_persistence_count = 0
            
        # Trigger Signal
        if self.arm_persistence_count >= self.arm_ticks:
            # Determine direction based on the last tick's state
            direction = SignalType.LONG if is_long_candidate else SignalType.SHORT
            
            # Reset validation
            self.arm_persistence_count = 0 
            
            return Signal(
                type=direction,
                symbol=tick.symbol,
                time=tick.timestamp,
                price=tick.price,
                reason=f"Velocity: {velocity:.5f} | Accel: True"
            )
            
        return None
