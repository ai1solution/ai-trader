"""
Caching utilities for market data.
"""
import pandas as pd
from pathlib import Path
from typing import Optional
import os

CACHE_DIR = Path("data/cache")

def ensure_cache_dir():
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache_path(symbol: str, start_str: str, end_str: str) -> Path:
    """
    Generate a cache file path.
    Symbol: BTC/USDT -> BTC_USDT
    """
    safe_symbol = symbol.replace("/", "_").replace(":", "_")
    filename = f"{safe_symbol}_{start_str}_{end_str}.parquet"
    return CACHE_DIR / filename

def load_cached_ohlcv(symbol: str, start_str: str, end_str: str) -> Optional[pd.DataFrame]:
    """
    Load OHLCV data from parquet cache.
    """
    path = get_cache_path(symbol, start_str, end_str)
    if path.exists():
        try:
            df = pd.read_parquet(path)
            # Ensure timestamp is datetime
            if 'timestamp' in df.columns:
                 df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            print(f"[Cache] Hit for {symbol}")
            return df
        except Exception as e:
            print(f"[Cache] Error loading {path}: {e}")
            return None
    return None

def save_to_cache(df: pd.DataFrame, symbol: str, start_str: str, end_str: str):
    """
    Save OHLCV data to parquet cache.
    """
    ensure_cache_dir()
    path = get_cache_path(symbol, start_str, end_str)
    try:
        # Ensure index is reset if it was timestamp
        df_to_save = df.copy()
        for col in df_to_save.columns:
            if pd.api.types.is_datetime64_any_dtype(df_to_save[col]):
                 # Force UTC
                 if df_to_save[col].dt.tz is None:
                     df_to_save[col] = df_to_save[col].dt.tz_localize('UTC')
                 else:
                     df_to_save[col] = df_to_save[col].dt.tz_convert('UTC')
                     
        df_to_save.to_parquet(path)
        print(f"[Cache] Saved {symbol} to {path}")
    except Exception as e:
         print(f"[Cache] Error saving {path}: {e}")
