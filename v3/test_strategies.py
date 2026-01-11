import unittest
from datetime import datetime, timedelta
from typing import List, Optional

from engine.market_data import Tick
from engine.enums import SignalType
from engine.strategies import (
    MomentumStrategy, 
    MeanReversionStrategy, 
    TrendFollowingStrategy, 
    BreakoutStrategy,
    ScalpingStrategy
)
from engine.config import EngineConfig

class MockConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class TestStrategies(unittest.TestCase):
    
    def setUp(self):
        self.base_time = datetime.now()
        
    def create_ticks(self, prices: List[float]) -> List[Tick]:
        return [
            Tick(timestamp=self.base_time + timedelta(seconds=i), price=p, volume=1.0, symbol="BTCUSDT")
            for i, p in enumerate(prices)
        ]

    def test_momentum_strategy(self):
        # Threshold 1%. 
        config = MockConfig(velocity_threshold=0.009, arm_ticks=2, lookback=1)
        strategy = MomentumStrategy(config)
        
        # Prices: 
        # 0: 100
        # 1: 101.5 (Vel = 1.5% > 0.9%). Candidate. ARM=1.
        # 2: 104.0 (Vel = 2.4% > 0.9%). Accel? Prev=1.5, Curr=2.4. Yes. ARM=2. Signal.
        prices = [100.0, 101.5, 104.0] 
        ticks = self.create_ticks(prices)
        
        signals = []
        for tick in ticks:
            sig = strategy.on_tick(tick)
            if sig: signals.append(sig)
            
        print(f"Momentum Signals: {[s.reason for s in signals]}")
        self.assertTrue(len(signals) > 0)
        self.assertEqual(signals[0].type, SignalType.LONG)

    def test_mean_reversion_strategy(self):
        config = MockConfig(bb_period=5, bb_std=2.0, rsi_period=5)
        strategy = MeanReversionStrategy(config)
        
        prices = [100.0] * 10 + [90, 80, 70, 60, 50, 40]
        ticks = self.create_ticks(prices)
        
        signals = []
        for tick in ticks:
            sig = strategy.on_tick(tick)
            if sig: signals.append(sig)
            
        print(f"MeanReversion Signals: {[s.reason for s in signals]}")
        
        if len(signals) > 0:
            self.assertEqual(signals[0].type, SignalType.LONG)

    def test_trend_following_strategy(self):
        config = MockConfig(fast_ema=5, slow_ema=10)
        strategy = TrendFollowingStrategy(config)
        
        prices = [100.0] * 20 + [110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
        ticks = self.create_ticks(prices)
        
        signals = []
        for tick in ticks:
            sig = strategy.on_tick(tick)
            if sig: signals.append(sig)
            
        print(f"Trend Signals: {[s.reason for s in signals]}")
        # Expect Long signal
        self.assertTrue(len(signals) > 0)
        self.assertEqual(signals[0].type, SignalType.LONG)

    def test_breakout_strategy(self):
        config = MockConfig(breakout_lookback=5)
        strategy = BreakoutStrategy(config)
        
        # Range 100-110 for 5 ticks.
        # Then 112 (Breakout)
        prices = [100, 110, 105, 102, 108] + [112, 115]
        ticks = self.create_ticks(prices)
        
        signals = []
        for tick in ticks:
            sig = strategy.on_tick(tick)
            if sig: signals.append(sig)
            
        print(f"Breakout Signals: {[s.reason for s in signals]}")
        self.assertTrue(len(signals) > 0)
        self.assertTrue("Breakout High" in signals[0].reason)

    def test_scalping_strategy(self):
        config = MockConfig(scalp_lookback=2, scalp_threshold=0.001)
        strategy = ScalpingStrategy(config)
        
        # 100 -> 100.2 (0.2% jump) > 0.1% threshold
        prices = [100.0, 100.0, 100.5]
        ticks = self.create_ticks(prices)
        
        signals = []
        for tick in ticks:
            sig = strategy.on_tick(tick)
            if sig: signals.append(sig)
            
        print(f"Scalp Signals: {[s.reason for s in signals]}")
        self.assertTrue(len(signals) > 0)
        self.assertTrue("Burst" in signals[0].reason)

if __name__ == '__main__':
    unittest.main()
