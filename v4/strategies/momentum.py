"""
Momentum Strategy (ARM port).
"Active Regime Momentum"
"""
from collections import deque
from typing import List, Dict, Any
from .interface import Strategy, Intent, FillEvent, Tick, OrderSide
from . import indicators

class MomentumStrategy(Strategy):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # Params
        self.lookback = config.get('momentum_lookback', 12)
        self.threshold = config.get('momentum_threshold', 0.0003)
        self.arm_ticks = config.get('arm_ticks', 3)
        self.rsi_period = config.get('rsi_period', 14)
        
        # State
        self.prices = deque(maxlen=300)
        self.velocities = deque(maxlen=300)
        self.arm_persistence = 0
        self.last_signal_side = None
        
        # Position tracking (Simplified, Engine handles real position, but strategy might want to know)
        self.position_size = 0.0

    def generate_signals(self, tick: Tick) -> List[Intent]:
        self.prices.append(tick.price)
        
        # 1. Calc Velocity
        velocity = indicators.calculate_velocity(list(self.prices), self.lookback)
        if velocity is None:
            return []
            
        self.velocities.append(velocity)
        # 2. Check Acceleration
        is_accelerating = indicators.calculate_velocity_acceleration(list(self.velocities))

        # 2b. Trend Filter
        trend_ema_period = self.config.get('trend_ema_period', 0)
        is_trend_long = True
        is_trend_short = True
        
        if trend_ema_period > 0:
            ema = indicators.calculate_ema(list(self.prices), trend_ema_period)
            if ema:
                is_trend_long = tick.price > ema
                is_trend_short = tick.price < ema

        # 3. Check RSI (Regime)
        rsi = indicators.calculate_rsi(list(self.prices), self.rsi_period)
        
        # 4. Long/Short Logic
        is_long = (
            velocity > self.threshold and
            is_accelerating and
            (rsi is None or rsi < 70) and
            is_trend_long
        )
        
        is_short = (
            velocity < -self.threshold and
            is_accelerating and
            (rsi is None or rsi > 30) and
            is_trend_short
        )
        
        # 5. ARM Persistence
        if is_long or is_short:
            self.arm_persistence += 1
        else:
            self.arm_persistence = 0
            
        # 6. Emit Intent
        if self.arm_persistence >= self.arm_ticks:
            side = OrderSide.BUY if is_long else OrderSide.SELL
            
            # Reset
            self.arm_persistence = 0
            
            return [Intent(
                strategy_name=self.name,
                symbol=tick.symbol,
                side=side,
                quantity=0.0, # Use Default/Max
                reason=f"Vel:{velocity:.5f}|Acc:{is_accelerating}"
            )]
            
        return []

    def on_fill(self, fill: FillEvent):
        # Update internal state if needed
        if fill.side == OrderSide.BUY:
            self.position_size += fill.quantity
        else:
            self.position_size -= fill.quantity # Simplified

    def on_bar_close(self, bar: Any):
        pass
