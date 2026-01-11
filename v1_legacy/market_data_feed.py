import time
import ccxt
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# --- Base Class ---
class MarketDataFeed:
    def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        """Returns current ticker data for list of symbols."""
        raise NotImplementedError

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 50) -> List[List]:
        """Returns OHLCV data ending at or before current time."""
        raise NotImplementedError

    def sleep(self, seconds: float):
        """Advances time (real or simulated)."""
        raise NotImplementedError

    def now(self) -> float:
        """Returns current timestamp in seconds (float)."""
        raise NotImplementedError

    def is_finished(self) -> bool:
        """Returns True if historical data is exhausted (always False for Live)."""
        return False

# --- Live Feed (Wrapper for CCXT) ---
class LiveFeed(MarketDataFeed):
    def __init__(self, items=None):
        # Items arg is just signature matching consistency if needed, but we init exchange here
        try:
            self.exchange = ccxt.kraken()
        except:
            self.exchange = None
            print("Warning: Failed to init Kraken in LiveFeed")
        self.last_tickers = {}

    def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        if not self.exchange: return {}
        try:
            self.last_tickers = self.exchange.fetch_tickers(symbols)
            return self.last_tickers
        except Exception as e:
            print(f"LiveFeed fetch error: {e}")
            return {}

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 50) -> List[List]:
        if not self.exchange: return []
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except:
            return []

    def sleep(self, seconds: float):
        time.sleep(seconds)

    def now(self) -> float:
        return time.time()

# --- Historical Feed (Simulator) ---
class HistoricalFeed(MarketDataFeed):
    def __init__(self, historical_data: Dict[str, Dict[int, Dict]], start_time_ms: int, end_time_ms: int, speed: str = "max"):
        """
        historical_data: Dict {symbol: {timestamp_ms: {o,h,l,c,v}}}
        """
        self.data = historical_data
        self.current_time_ms = start_time_ms
        self.end_time_ms = end_time_ms
        self.speed = speed # "realtime", "10x", "max"
        
        # Pre-process symbols list
        self.symbols = list(self.data.keys())
        
        # Tick State Cache (Current interpolated price)
        self.current_prices = {sym: 0.0 for sym in self.symbols}
        
    def _interpolate_price(self, symbol: str, time_ms: int) -> float:
        """
        Interpolates price for a specific millisecond timestamp based on the 1m candle it falls into.
        Strategy: Open -> High -> Low -> Close over the minute.
        """
        # Find the 1m candle start
        candle_start_ms = (time_ms // 60000) * 60000
        candle = self.data.get(symbol, {}).get(candle_start_ms)
        
        if not candle:
            # Fallback to previous close or last known
            # Ideally strictly previous candle close, but for simplicity returning last known
            return self.current_prices.get(symbol, 0.0)

        o, h, l, c = candle['o'], candle['h'], candle['l'], candle['c']
        
        # Offset within the minute (0 to 59999 ms)
        offset = time_ms - candle_start_ms
        
        # 0-20s: Open -> High
        # 20-40s: High -> Low
        # 40-60s: Low -> Close
        
        if offset < 20000:
            ratio = offset / 20000
            price = o + (h - o) * ratio
        elif offset < 40000:
            ratio = (offset - 20000) / 20000
            price = h + (l - h) * ratio
        else:
            ratio = (offset - 40000) / 20000
            price = l + (c - l) * ratio
            
        return price

    def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        """Returns synthetic tickers at current_time_ms."""
        tickers = {}
        
        for sym in symbols:
            price = self._interpolate_price(sym, self.current_time_ms)
            self.current_prices[sym] = price
            
            # Synthetic spread (e.g. 0.05%)
            spread = 0.0005 * price 
            bid = price - (spread/2)
            ask = price + (spread/2)
            
            tickers[sym] = {
                'symbol': sym,
                'timestamp': self.current_time_ms,
                'datetime': datetime.fromtimestamp(self.current_time_ms/1000, tz=timezone.utc).isoformat(),
                'high': price, # Approximation
                'low': price,  # Approximation
                'bid': bid,
                'ask': ask,
                'vwap': price,
                'open': price,
                'close': price,
                'last': price,
                'previousClose': price, # Not tracking for now
                'change': 0,
                'percentage': 0,
                'average': price,
                'baseVolume': 0,
                'quoteVolume': 0,
            }
        return tickers

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 50) -> List[List]:
        """
        Returns candles STRICTLY from the past relative to current_time_ms.
        No future leakage.
        """
        if timeframe != '1m':
            return [] # Only supporting 1m replay for now
            
        repo = self.data.get(symbol, {})
        if not repo: return []
        
        # current min start
        current_candle_start = (self.current_time_ms // 60000) * 60000
        
        # Return candles < current_candle_start
        # Because the current minute is "in progress", engines usually look at closed candles.
        # If the engine accepts the forming candle, we could include it, but strict standard is closed candles.
        
        valid_timestamps = [ts for ts in repo.keys() if ts < current_candle_start]
        valid_timestamps.sort()
        
        subset = valid_timestamps[-limit:]
        
        result = []
        for ts in subset:
            c = repo[ts]
            # [timestamp, open, high, low, close, volume]
            result.append([ts, c['o'], c['h'], c['l'], c['c'], c['v']])
            
        return result

    def sleep(self, seconds: float):
        """Simulates time passage."""
        ms_increment = int(seconds * 1000)
        self.current_time_ms += ms_increment
        
        # Handle Replay Speed
        if self.speed == "realtime":
            time.sleep(seconds)
        elif self.speed == "10x":
            time.sleep(seconds / 10)
        # "max" speed = no sleep

    def now(self) -> float:
        return self.current_time_ms / 1000.0

    def is_finished(self) -> bool:
        return self.current_time_ms >= self.end_time_ms
