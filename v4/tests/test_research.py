"""
Test Research Components (Universe, Regime, Portfolio, Protection).
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from v4.engine.universe import UniverseSelector
from v4.engine.regime import RegimeClassifier, MarketRegime
from v4.engine.portfolio import Portfolio
from v4.engine.engine import TradingEngine, TradingState, Strategy

@pytest.mark.asyncio
async def test_universe_selector():
    config = {'universe': {'min_price': 1.0, 'min_volume_24h': 1000.0, 'min_atr_pct': 0.01}}
    selector = UniverseSelector(config)
    selector.provider.fetch_ohlcv = AsyncMock()
    
    # Mock Data: Price=10, Vol=2000 (Passes), ATR=low
    # Need to simulate specific return for different symbols?
    # Simple check on blacklist
    selector.blacklist = ["BAD/USDT"]
    
    res = await selector.select_symbols(["GOOD/USDT", "BAD/USDT"])
    # We expect BAD to be filtered invalidly if we don't mock fetch_ohlcv properly.
    # But checking blacklist logic first.
    # Actually, select_symbols does blacklist check first.
    # mocking fetch_ohlcv to return None (error) for GOOD so it fails data check but passes blacklist.
    
    selector.provider.fetch_ohlcv.return_value = None
    res = await selector.select_symbols(["BAD/USDT"])
    assert "BAD/USDT" not in res
    
@pytest.mark.asyncio
async def test_regime_classification():
    regime = RegimeClassifier()
    regime.provider.fetch_ohlcv = AsyncMock()
    
    # Test internal logic by injecting data directly if possible, or mocking fetch to return Trending Pattern
    # For now, just ensuring it can run without error
    res = await regime.get_regime("BTC/USDT", datetime.now())
    # Should default to UNCERTAIN if no data
    assert res == MarketRegime.UNCERTAIN

def test_portfolio_allocation():
    p = Portfolio(10000.0)
    
    # 1. Request valid
    amt = p.request_allocation("BTC", "mom", 1000.0)
    assert amt == 1000.0
    assert p.allocations["BTC"] == 1000.0
    
    # 2. Request exceeding symbol cap (20% = 2000)
    amt = p.request_allocation("BTC", "mom", 1500.0) # Total 2500 > 2000
    assert amt == 0.0
    assert p.allocations["BTC"] == 1000.0
    
    # 3. Release
    p.release_allocation("BTC", "mom", 1000.0, 100.0) # +100 profit
    assert p.allocations["BTC"] == 0.0
    assert p.current_capital == 10100.0

def test_protection_logic():
    eng = TradingEngine("BTC", MagicMock(), use_protection=True)
    
    # Simulate 2 losses
    eng.consecutive_losses = 1
    
    # Mock config/portfolio not needed for this logic check
    
    # Close position with loss
    eng._close_position = MagicMock(wraps=eng._close_position) # wrapper? No, just call it or simulate logic
    # _close_position inside logic:
    # We can test logic block directly or subclass/mock.
    # It sets consecutive_losses
    
    # Let's manually trigger the logic block equivalents or minimal context
    # Better: Instantiate engine and call _close_position with a dummy Position
    from v4.engine.engine import Position, OrderSide
    eng.position = Position("BTC", OrderSide.BUY, 100, 1, datetime.now())
    
    # Mock portfolio to avoid error
    eng.portfolio = MagicMock()
    
    # Loss 2
    class Tick:
        pass
    t = Tick(); t.price=90; t.timestamp=datetime.now()
    
    eng.regime_classifier = MagicMock() # Exist but maybe returns whatever
    # We need to run the code. _close_position checks pnl.
    # Entry 100, Exit 90 -> Loss.
    
    eng._close_position(t, "SL")
    
    assert eng.consecutive_losses == 2
    assert eng.state == TradingState.DISABLED
