"""
Exchange API client for fetching historical and live data.

Supports:
- Binance REST API for historical candles
- Binance WebSocket for live trade stream

Future: Add Coinbase, Kraken support.
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from pathlib import Path
import time


def fetch_binance_candles(
    symbol: str,
    start_time: datetime,
    end_time: datetime,
    timeframe: str = '1m'
) -> pd.DataFrame:
    """
    Fetch historical 1m candles from Binance REST API.
    
    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        start_time: Start of data range (UTC)
        end_time: End of data range (UTC)
        timeframe: Candle timeframe (default '1m')
        
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
        
    Raises:
        Exception: If API call fails or data validation fails
    """
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
        }
    })
    
    # Convert to milliseconds
    since = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    all_candles = []
    current_since = since
    
    # Pagination: Binance returns max 1000 candles per request
    while current_since < end_ms:
        try:
            candles = exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=current_since,
                limit=1000
            )
            
            if not candles:
                break
                
            all_candles.extend(candles)
            
            # Update since to last candle timestamp + 1 minute
            current_since = candles[-1][0] + 60000
            
            # Rate limiting
            time.sleep(exchange.rateLimit / 1000.0)
            
        except Exception as e:
            raise Exception(f"Binance API error: {e}")
    
    # Convert to DataFrame
    if not all_candles:
        raise Exception(f"No candles fetched for {symbol} from {start_time} to {end_time}")
    
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Convert timestamp to datetime (UTC)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    
    # Filter to exact range
    df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df


def validate_candles(df: pd.DataFrame, timeframe: str = '1m'):
    """
    Validate candle data integrity.
    
    Checks:
    - No missing candles (gaps in timestamps)
    - Monotonic increasing timestamps
    - UTC timezone
    
    Args:
        df: Candles DataFrame
        timeframe: Expected timeframe (default '1m')
        
    Raises:
        ValueError: If validation fails
    """
    if df.empty:
        raise ValueError("Empty candle DataFrame")
    
    # Check monotonic timestamps
    if not df['timestamp'].is_monotonic_increasing:
        raise ValueError("Timestamps are not monotonically increasing")
    
    # Check for UTC timezone
    if df['timestamp'].dt.tz is None:
        raise ValueError("Timestamps must be timezone-aware (UTC)")
    
    # Check for gaps (missing candles)
    # For 1m timeframe, expect 60-second intervals
    if timeframe == '1m':
        expected_delta = pd.Timedelta(minutes=1)
        time_diffs = df['timestamp'].diff()[1:]  # Skip first (NaT)
        
        # Allow small tolerance for timestamp jitter
        tolerance = pd.Timedelta(seconds=2)
        
        gaps = time_diffs[time_diffs > (expected_delta + tolerance)]
        
        if not gaps.empty:
            gap_indices = gaps.index.tolist()
            raise ValueError(
                f"Found {len(gaps)} gaps in candle data at indices: {gap_indices[:10]}"
            )
    
    print(f"✓ Candle validation passed: {len(df)} candles, {df['timestamp'].min()} to {df['timestamp'].max()}")


def cache_candles(df: pd.DataFrame, cache_path: Path, format: str = 'parquet'):
    """
    Save candles to disk cache.
    
    Args:
        df: Candles DataFrame
        cache_path: Path to cache file
        format: 'csv' or 'parquet' (default 'parquet' for efficiency)
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'parquet':
        df.to_parquet(cache_path, index=False)
    elif format == 'csv':
        df.to_csv(cache_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    print(f"✓ Cached {len(df)} candles to {cache_path}")


def load_cached_candles(cache_path: Path) -> Optional[pd.DataFrame]:
    """
    Load candles from cache if available.
    
    Args:
        cache_path: Path to cache file
        
    Returns:
        DataFrame if cache exists and is valid, None otherwise
    """
    if not cache_path.exists():
        return None
    
    try:
        if cache_path.suffix == '.parquet':
            df = pd.read_parquet(cache_path)
        elif cache_path.suffix == '.csv':
            df = pd.read_csv(cache_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        else:
            return None
        
        print(f"✓ Loaded {len(df)} candles from cache: {cache_path}")
        return df
        
    except Exception as e:
        print(f"⚠ Failed to load cache: {e}")
        return None


# Future: WebSocket live feed implementation
def subscribe_binance_trades(symbol: str, callback: Callable):
    """
    Subscribe to Binance WebSocket trade stream.
    
    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        callback: Function to call for each trade event
        
    Note: This is a placeholder for future implementation.
    Full implementation requires asyncio WebSocket client.
    """
    raise NotImplementedError("Live WebSocket feed not yet implemented")

def fetch_ticker_snapshot(symbols: List[str]) -> dict:
    """
    Fetch current snapshot for a list of symbols.
    """
    exchange = ccxt.binance()
    try:
        # ccxt expects symbols in format "BTC/USDT"
        tickers = exchange.fetch_tickers(symbols)
        return tickers
    except Exception as e:
        print(f"Error fetching snapshot: {e}")
        return {}
