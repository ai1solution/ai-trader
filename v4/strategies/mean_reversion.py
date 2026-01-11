"""
Mean Reversion Strategy.
Bollinger Bands + RSI.
"""
from collections import deque
from typing import List
from .interface import Strategy, Intent, FillEvent, Tick, OrderSide
from . import indicators

class MeanReversionStrategy(Strategy):
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
        self.rsi_period = config.get('rsi_period', 14)
        
        self.prices = deque(maxlen=300)
        
    def generate_signals(self, tick: Tick) -> List[Intent]:
        self.prices.append(tick.price)
        
        if len(self.prices) < self.bb_period:
            return []
            
        # 1. Bollinger Bands
        bb = indicators.calculate_bollinger_bands(list(self.prices), self.bb_period, self.bb_std)
        if not bb: return []
        upper, mid, lower = bb
        
        # 2. RSI
        rsi = indicators.calculate_rsi(list(self.prices), self.rsi_period)
        if not rsi: return []
        
        # 3. Logic
        # Trend Filter
        trend_ema_period = self.config.get('trend_ema_period', 0)
        is_trend_long = True
        is_trend_short = True
        
        if trend_ema_period > 0:
            ema = indicators.calculate_ema(list(self.prices), trend_ema_period)
            if ema:
                is_trend_long = tick.price > ema
                is_trend_short = tick.price < ema

        # Buy if Price < Lower Band AND RSI < 30 (Oversold) AND Trend is Long (Buy the dip)
        if tick.price < lower and rsi < 30 and is_trend_long:
            return [Intent(self.name, tick.symbol, OrderSide.BUY, 0.0, reason="BB_Lower+RSI_Oversold")]
            
        # Sell if Price > Upper Band AND RSI > 70 (Overbought) AND Trend is Short (Sell the rip)
        elif tick.price > upper and rsi > 70 and is_trend_short:
            return [Intent(self.name, tick.symbol, OrderSide.SELL, 0.0, reason="BB_Upper+RSI_Overbought")]
            
        return []

    def on_fill(self, fill: FillEvent):
        pass

    def on_bar_close(self, bar):
        pass
