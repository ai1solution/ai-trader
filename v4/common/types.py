"""
Common types and utilities for the v4 trading engine.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional, Dict, List, Any

# --- Time Utilities ---

def normalize_timestamp(ts: Any) -> datetime:
    """
    Ensure timestamp is a timezone-aware UTC datetime.
    Accepts: int (ms), str (iso), datetime.
    """
    if isinstance(ts, int) or isinstance(ts, float):
        # Assume milliseconds if large, seconds if small? 
        # CCXT uses milliseconds. Start with ms assumption for > 1990
        if ts > 3000000000: # Rough cutoff, 1970 + a bit vs now
            return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    
    if isinstance(ts, str):
        # ISO format
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
        
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
        
    raise ValueError(f"Unsupported timestamp format: {type(ts)} - {ts}")

# --- Math Utilities ---

def round_price(price: float) -> float:
    """Round price to 8 decimal places."""
    return round(price, 8)

def round_qty(qty: float) -> float:
    """Round quantity down to 8 decimal places."""
    import math
    factor = 10**8
    return math.floor(qty * factor) / factor

def format_price(price: float) -> str:
    """Format price with dynamic precision up to 8 decimals."""
    return f"{price:.8f}".rstrip('0').rstrip('.')


# --- Core Data Structures ---

@dataclass
class Tick:
    """
    A single market tick (price update).
    """
    timestamp: datetime
    price: float
    volume: float = 0.0
    symbol: str = ""
    is_candle_close: bool = False

    def __repr__(self):
        return f"Tick({self.symbol}, {self.timestamp.strftime('%H:%M:%S')}, {format_price(self.price)})"

@dataclass
class Candle:
    """
    OHLCV Candle.
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""

# --- Enums ---

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class TimeFrame(Enum):
    m1 = "1m"
    m5 = "5m"
    m15 = "15m"
    h1 = "1h"
    h4 = "4h"
    d1 = "1d"
