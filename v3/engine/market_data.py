"""
Market data abstraction layer.

The trading engine doesn't know where data comes from.
Same interface for live, replay, paper trading, etc.

Key principle: Replay mode must be deterministic.
1m candles → 2s ticks using OHLC interpolation.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import pandas as pd


class Tick:
    """
    A single market tick.
    
    Attributes:
        timestamp: Time of tick (engine time, not wall-clock time)
        price: Current price
        volume: Volume (can be interpolated for sub-candle ticks)
        is_candle_close: True if this tick represents candle close
    """
    def __init__(self, timestamp: datetime, price: float, volume: float = 0.0,
                 is_candle_close: bool = False, symbol: str = ""):
        self.timestamp = timestamp
        self.price = price
        self.volume = volume
        self.is_candle_close = is_candle_close
        self.symbol = symbol
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "volume": self.volume,
            "is_candle_close": self.is_candle_close
        }
        
    def __repr__(self) -> str:
        return f"Tick(ts={self.timestamp}, price={self.price:.2f}, vol={self.volume:.2f})"


class MarketDataFeed(ABC):
    """
    Abstract interface for market data.
    
    Engine only depends on this interface, not on implementation.
    This allows same engine code to work with:
    - HistoricalFeed (replay)
    - LiveFeed (real-time)
    - PaperFeed (simulated)
    """
    
    @abstractmethod
    def get_next_tick(self) -> Optional[Tick]:
        """
        Get next tick.
        
        Returns:
            Tick object, or None if feed exhausted
        """
        pass
    
    @abstractmethod
    def has_more_data(self) -> bool:
        """Check if more data is available."""
        pass
    
    @abstractmethod
    def get_current_time(self) -> datetime:
        """Get current engine time (not wall-clock time)."""
        pass


class HistoricalFeed(MarketDataFeed):
    """
    Historical data feed for replay mode.
    
    Loads 1-minute candles and interpolates to 2-second ticks.
    
    Interpolation logic:
    - Each 1m candle is split into N ticks (30 ticks for 2s interval)
    - Tick prices follow OHLC pattern:
      - First tick: Open price
      - Next ticks: Linear interpolation O → H
      - Middle ticks: Linear interpolation H → L
      - Later ticks: Linear interpolation L → C
      - Last tick: Close price (marked as is_candle_close=True)
    
    Why this matters:
    - Realistic intra-candle price movement
    - Deterministic (same candles → same ticks)
    - Allows fine-grained state transitions
    """
    
    def __init__(self, candles_df: pd.DataFrame, tick_interval_seconds: float = 2.0):
        """
        Initialize historical feed.
        
        Args:
            candles_df: DataFrame with columns: timestamp, open, high, low, close, volume
            tick_interval_seconds: Time between ticks (default 2s)
        """
        self.candles_df = candles_df.copy()
        self.tick_interval_seconds = tick_interval_seconds
        
        # Calculate ticks per candle (assuming 1m candles)
        self.ticks_per_candle = int(60 / tick_interval_seconds)
        
        # Generate all ticks upfront for determinism
        self.ticks = self._generate_ticks()
        self.current_index = 0
        
    def _generate_ticks(self) -> List[Tick]:
        """
        Generate all ticks from candles.
        
        Returns:
            List of Tick objects
        """
        all_ticks = []
        
        for idx, row in self.candles_df.iterrows():
            candle_timestamp = pd.to_datetime(row['timestamp'])
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            candle_volume = row['volume']
            
            # Volume distributed evenly across ticks
            tick_volume = candle_volume / self.ticks_per_candle
            
            candle_ticks = self._interpolate_candle(
                candle_timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                tick_volume
            )
            
            all_ticks.extend(candle_ticks)
            
        return all_ticks
    
    def _interpolate_candle(self, timestamp: datetime, open_p: float, high_p: float,
                           low_p: float, close_p: float, tick_volume: float) -> List[Tick]:
        """
        Interpolate a single candle into ticks.
        
        Pattern: O → H → L → C
        
        Args:
            timestamp: Candle start time
            open_p, high_p, low_p, close_p: OHLC prices
            tick_volume: Volume per tick
            
        Returns:
            List of Tick objects for this candle
        """
        ticks = []
        tick_interval = timedelta(seconds=self.tick_interval_seconds)
        
        # Divide ticks into 4 phases: O→H (25%), H→L (25%), L→C (50%)
        # This creates realistic intra-candle movement
        n = self.ticks_per_candle
        phase1_ticks = max(1, n // 4)  # O → H
        phase2_ticks = max(1, n // 4)  # H → L  
        phase3_ticks = n - phase1_ticks - phase2_ticks  # L → C
        
        current_time = timestamp
        tick_count = 0
        
        # Phase 1: Open → High
        for i in range(phase1_ticks):
            progress = i / phase1_ticks if phase1_ticks > 1 else 0
            price = open_p + (high_p - open_p) * progress
            ticks.append(Tick(current_time, price, tick_volume))
            current_time += tick_interval
            tick_count += 1
            
        # Phase 2: High → Low
        for i in range(phase2_ticks):
            progress = i / phase2_ticks if phase2_ticks > 1 else 0
            price = high_p + (low_p - high_p) * progress
            ticks.append(Tick(current_time, price, tick_volume))
            current_time += tick_interval
            tick_count += 1
            
        # Phase 3: Low → Close
        for i in range(phase3_ticks):
            progress = (i + 1) / phase3_ticks  # +1 to reach close on last tick
            price = low_p + (close_p - low_p) * progress
            is_last = (tick_count == n - 1)
            ticks.append(Tick(current_time, price, tick_volume, is_candle_close=is_last))
            current_time += tick_interval
            tick_count += 1
            
        return ticks
    
    def get_next_tick(self) -> Optional[Tick]:
        """Get next tick from feed."""
        if self.current_index >= len(self.ticks):
            return None
            
        tick = self.ticks[self.current_index]
        self.current_index += 1
        return tick
    
    def has_more_data(self) -> bool:
        """Check if more ticks available."""
        return self.current_index < len(self.ticks)
    
    def get_current_time(self) -> datetime:
        """Get current engine time."""
        if self.current_index == 0:
            return self.ticks[0].timestamp if self.ticks else datetime.now()
        elif self.current_index >= len(self.ticks):
            return self.ticks[-1].timestamp if self.ticks else datetime.now()
        else:
            return self.ticks[self.current_index - 1].timestamp


class LiveFeed(MarketDataFeed):
    """
    Live data feed using REST API polling.
    
    Fetches latest price every N seconds from exchange REST API.
    Simpler than WebSocket but sufficient for mock trading.
    """
    
    def __init__(self, symbol: str, exchange: str = "binance", poll_interval: float = 2.0):
        """
        Initialize live feed with REST polling.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            exchange: Exchange name (default "binance")
            poll_interval: Seconds between API polls (default 2.0)
        """
        import ccxt
        from datetime import timezone
        
        self.symbol = symbol
        self.exchange_name = exchange
        self.poll_interval = poll_interval
        self.running = True
        
        # Initialize exchange
        if exchange == "binance":
            self.exchange = ccxt.binance({'enableRateLimit': True})
        else:
            raise NotImplementedError(f"Exchange {exchange} not supported yet")
        
        # Convert symbol format (BTCUSDT -> BTC/USDT)
        self.api_symbol = symbol.replace("USDT", "/USDT") if "/" not in symbol else symbol
        
        self.last_poll_time = None
        
    def get_next_tick(self) -> Optional[Tick]:
        """
        Get next tick by polling exchange REST API.
        
        Returns:
            Tick object with latest price, or None if error
        """
        import time
        from datetime import timezone
        
        # Rate limiting: don't poll faster than poll_interval
        if self.last_poll_time is not None:
            elapsed = time.time() - self.last_poll_time
            if elapsed < self.poll_interval:
                time.sleep(self.poll_interval - elapsed)
        
        try:
            # Fetch latest ticker
            ticker = self.exchange.fetch_ticker(self.api_symbol)
            
            # Create tick from ticker data
            price = ticker['last']  # Last trade price
            timestamp = datetime.fromtimestamp(ticker['timestamp'] / 1000, tz=timezone.utc)
            volume = ticker.get('baseVolume', 0.0)
            
            self.last_poll_time = time.time()
            
            return Tick(timestamp=timestamp, price=price, volume=volume)
            
        except Exception as e:
            print(f"Error fetching tick for {self.symbol}: {e}")
            return None
    
    def has_more_data(self) -> bool:
        """Live feed continues until stopped."""
        return self.running
    
    def get_current_time(self) -> datetime:
        """Live feed uses current wall-clock time (UTC)."""
        from datetime import timezone
        return datetime.now(timezone.utc)
    
    def stop(self):
        """Stop the live feed."""
        self.running = False


class HistoricalAPIDataFeed(MarketDataFeed):
    """
    Historical data feed that fetches from exchange REST API.
    
    Workflow:
    1. Try to load candles from cache
    2. If not cached or incomplete, fetch from exchange API
    3. Validate data (no gaps, monotonic timestamps, UTC)
    4. Cache to disk for future runs
    5. Use HistoricalFeed to interpolate and feed ticks
    
    This ensures:
    - First run: Fetches from API and caches
    - Subsequent runs: Uses cache (deterministic replay)
    - Replay mode NEVER hits live APIs
    """
    
    def __init__(self,
                 symbol: str,
                 start_time: datetime,
                 end_time: datetime,
                 exchange: str = "binance",
                 cache_dir: str = "data/cache",
                 tick_interval_seconds: float = 2.0):
        """
        Initialize historical API feed.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT" or "BTC/USDT")
            start_time: Start of data range (UTC)
            end_time: End of data range (UTC)
            exchange: Exchange name ("binance", future: "coinbase", "kraken")
            cache_dir: Directory for cached candles
            tick_interval_seconds: Tick interval for interpolation
        """
        from pathlib import Path
        from . import api_client
        
        self.symbol = symbol
        self.start_time = start_time
        self.end_time = end_time
        self.exchange = exchange
        self.tick_interval_seconds = tick_interval_seconds
        
        # Normalize symbol for file naming (BTC/USDT -> BTCUSDT)
        symbol_clean = symbol.replace('/', '')
        
        # Cache path
        cache_path = Path(cache_dir) / f"{symbol_clean}_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.parquet"
        
        # Try to load from cache
        candles_df = api_client.load_cached_candles(cache_path)
        
        if candles_df is None:
            print(f"Cache miss. Fetching {symbol} from {exchange} API...")
            
            # Fetch from API
            if exchange == "binance":
                # Convert BTCUSDT to BTC/USDT if needed
                api_symbol = symbol if '/' in symbol else f"{symbol[:3]}/{symbol[3:]}"
                candles_df = api_client.fetch_binance_candles(
                    api_symbol,
                    start_time,
                    end_time
                )
            else:
                raise NotImplementedError(f"Exchange {exchange} not yet supported")
            
            # Validate data
            api_client.validate_candles(candles_df)
            
            # Cache for future runs
            api_client.cache_candles(candles_df, cache_path, format='parquet')
        
        # Create internal HistoricalFeed for tick interpolation
        self._feed = HistoricalFeed(candles_df, tick_interval_seconds)
        
        print(f"✓ HistoricalAPIDataFeed ready: {len(candles_df)} candles → {len(self._feed.ticks)} ticks")
    
    def get_next_tick(self) -> Optional[Tick]:
        """Get next tick (delegates to internal HistoricalFeed)."""
        return self._feed.get_next_tick()
    
    def has_more_data(self) -> bool:
        """Check if more data available."""
        return self._feed.has_more_data()
    
    def get_current_time(self) -> datetime:
        """Get current engine time."""
        return self._feed.get_current_time()


class LiveAPIDataFeed(MarketDataFeed):
    """
    Live data feed via exchange WebSocket.
    
    Subscribes to real-time trade stream and feeds ticks directly to engine.
    
    IMPORTANT DIFFERENCES FROM HISTORICAL:
    - No interpolation (1 WebSocket event = 1 tick)
    - Uses wall-clock time (UTC)
    - Async/blocking (waits for real market events)
    
    NOTE: This is a placeholder for future full implementation.
    Full WebSocket integration requires asyncio event loop.
    """
    
    def __init__(self,
                 symbol: str,
                 exchange: str = "binance",
                 stream_type: str = "trades"):
        """
        Initialize live API feed.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            exchange: Exchange name ("binance")
            stream_type: "trades" or "ticker" (future: best bid/ask)
        """
        self.symbol = symbol
        self.exchange = exchange
        self.stream_type = stream_type
        self.connected = False
        
        # TODO: Full implementation would:
        # 1. Connect to WebSocket (ccxt.watch_trades or websocket-client)
        # 2. Start background thread to receive messages
        # 3. Queue incoming ticks
        # 4. Handle reconnection logic
        
        print(f"⚠ LiveAPIDataFeed is a placeholder. Full WebSocket not yet implemented.")
        print(f"   Symbol: {symbol}, Exchange: {exchange}")
    
    def get_next_tick(self) -> Optional[Tick]:
        """
        Get next tick from live stream.
        
        Full implementation would:
        - Poll internal tick queue (populated by WebSocket thread)
        - Block or use timeout until tick available
        - Return Tick(timestamp=trade_time, price=trade_price, volume=trade_size)
        """
        # Placeholder: return None
        return None
    
    def has_more_data(self) -> bool:
        """Live feed always has more data (until disconnected)."""
        return self.connected
    
    def get_current_time(self) -> datetime:
        """Live feed uses wall-clock time (UTC)."""
        from datetime import timezone
        return datetime.now(timezone.utc)
    
    def close(self):
        """Close WebSocket connection (future implementation)."""
        self.connected = False
