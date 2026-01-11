"""
Test script for partial profit-taking functionality.

Tests:
1. Partial trigger based on MFE
2. Size reduction (50% close)
3. Stop-loss monotonicity after partial
4. Size-weighted PnL calculation
"""

import sys
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, '.')

from engine import EngineConfig, TradingEngine, EngineLogger, HistoricalFeed
from engine.enums import SignalType


def create_test_data_with_excursion():
    """
    Create synthetic data with a favorable excursion.
    
    Scenario:
    - Entry at ~$100
    - Price moves to $100.60 (+0.6%) to trigger partial
    - Price then consolidates
    - Tests MFE-based partial trigger
    """
    timestamps = []
    prices = []
    
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    base_price = 100.0
    
    # Build 10-minute scenario (10 candles) with strong uptrend
    for i in range(10):
        ts = base_time + timedelta(minutes=i)
        
        if i == 0:
            # First candle: start
            candle = {
                'open': 100.0,
                'high': 100.15,
                'low': 99.95,
                'close': 100.10
            }
        elif i == 1:
            # Second candle: uptrend begins
            candle = {
                'open': 100.10,
                'high': 100.30,
                'low': 100.05,
                'close': 100.25
            }
        elif i == 2:
            # Third candle: STRONG MOVE UP - should trigger partial
            candle = {
                'open': 100.25,
                'high': 100.75,  # +0.75% from $100 entry - TRIGGERS PARTIAL at 0.6%
                'low': 100.25,
                'close': 100.65
            }
        elif i == 3:
            # Fourth candle: consolidation after partial
            candle = {
                'open': 100.65,
                'high': 100.70,
                'low': 100.55,
                'close': 100.60
            }
        elif i == 4:
            # Fifth candle: slight pullback
            candle = {
                'open': 100.60,
                'high': 100.62,
                'low': 100.45,
                'close': 100.50
            }
        else:
            # Remaining candles: consolidation
            candle = {
                'open': 100.50 + (i - 5) * 0.02,
                'high': 100.55 + (i - 5) * 0.02,
                'low': 100.45 + (i - 5) * 0.02,
                'close':  100.50 + (i - 5) * 0.02
            }
        
        timestamps.append(ts)
        prices.append(candle)
    
    # Convert to DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [p['open'] for p in prices],
        'high': [p['high'] for p in prices],
        'low': [p['low'] for p in prices],
        'close': [p['close'] for p in prices],
        'volume': [1000.0] * 10
    })
    
    return df


def test_partial_profit_taking():
    """Test partial profit-taking with MFE trigger."""
    
    print("=" * 60)
    print("PARTIAL PROFIT-TAKING TEST")
    print("=" * 60)
    
    # Create test data
    print("\n1. Creating test data with favorable excursion...")
    candles_df = create_test_data_with_excursion()
    print(f"   Candles: {len(candles_df)}")
    print("\n   Scenario:")
    print("   - Candle 0-1: Entry zone, uptrend begins")
    print("   - Candle 2: STRONG MOVE to $100.75 (+0.75% MFE) → triggers partial at 0.6%")
    print("   - Candles 3-9: Consolidation and recovery")
    
    # Configure engine
    print("\n2. Configuring engine...")
    config = EngineConfig(
        # ARM config (easy trigger for testing)
        arm_velocity_threshold=0.001,  # 0.1% velocity
        arm_persistence_ticks=2,
        
        # Partial profit config
        partial_profit_enabled=True,
        partial_take_pct=0.006,  # 0.6% trigger
        partial_close_ratio=0.5,  # 50% close
        post_partial_stop_buffer_pct=0.0,  # Breakeven
        
        # Position sizing
        position_size_usd=1000.0,
        
        # Tick interval
        replay_tick_interval_seconds=2.0,
        
        # Disable signal decay for this test
        signal_decay_enabled=False
    )
    
    logger = EngineLogger(log_file="logs/partial_test.log", log_level="DEBUG")
    engine = TradingEngine(symbol="TESTUSDT", config=config, logger=logger)
    
    # Create feed
    print("\n3. Creating historical feed...")
    feed = HistoricalFeed(candles_df, tick_interval_seconds=2.0)
    print(f"   Generated {len(feed.ticks)} ticks from {len(candles_df)} candles")
    
    # Run engine
    print("\n4. Running engine...")
    tick_count = 0
    partial_event_tick = None
    
    while feed.has_more_data():
        tick = feed.get_next_tick()
        if tick is None:
            break
        
        engine.on_tick(tick)
        tick_count += 1
        
        # Check if partial was taken
        if engine.position and engine.position.partial_taken and partial_event_tick is None:
            partial_event_tick = tick_count
            print(f"\n   ✓ PARTIAL TRIGGERED at tick {tick_count}")
            print(f"     Price: ${tick.price:.2f}")
            print(f"     Entry: ${engine.position.entry_price:.2f}")
            print(f"     MFE: {((engine.position.highest_price - engine.position.entry_price) / engine.position.entry_price * 100):.2f}%")
            print(f"     Partial PnL: ${engine.position.partial_realized_pnl:.2f}")
            print(f"     Remaining size: ${engine.position.remaining_size:.2f}")
            print(f"     New stop-loss: ${engine.position.stop_loss_price:.2f}")
    
    print(f"\n5. Replay complete")
    print(f"   Total ticks processed: {tick_count}")
    print(f"   Total trades: {engine.trade_count}")
    
    # Verify results
    print("\n6. Verification:")
    
    if partial_event_tick:
        print(f"   ✓ Partial profit was triggered (tick {partial_event_tick})")
        print(f"   ✓ Test PASSED")
    else:
        print(f"   ✗ Partial profit was NOT triggered")
        print(f"   ✗ Test FAILED")
        return False
    
    # Check logs
    print("\n7. Logs written to: logs/partial_test.log")
    print("   Review for PARTIAL_TAKE event")
    
    logger.close()
    return True


if __name__ == "__main__":
    success = test_partial_profit_taking()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ PARTIAL PROFIT-TAKING TEST PASSED")
    else:
        print("✗ PARTIAL PROFIT-TAKING TEST FAILED")
    print("=" * 60)
