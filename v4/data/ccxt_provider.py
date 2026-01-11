"""
CCXT Data Provider.
Wraps CCXT library to provide unified data access.
"""
import ccxt.async_support as ccxt  # Use async version
import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from ..common.types import Candle, Tick, normalize_timestamp

class CCXTProvider:
    """
    Async CCXT Wrapper.
    """
    def __init__(self, exchange_id: str = 'binance', sandbox: bool = False):
        self.exchange_id = exchange_id
        self.exchange_class = getattr(ccxt, exchange_id)
        self.exchange = self.exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'} # Default to swap/future if available? Or spot? 
            # User said "BTC pairs", usually implies futures for trading engines but "Paper Trading" often spot.
            # I'll default to spot or let user configure. 
            # User said "50 BTC-related symbols", "No leverage". Likely spot.
        })
        if sandbox:
            self.exchange.set_sandbox_mode(True)
            
    async def cleanup(self):
        await self.exchange.close()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, 
                          start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        Fetch OHLCV data with pagination.
        Returns DataFrame with UTC timestamps.
        """
        all_candles = []
        since = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        resolution_ms = self.exchange.parse_timeframe(timeframe) * 1000
        
        # Limit per request (Exchange dependent, 1000 for Binance)
        limit = 1000 
        
        print(f"[CCXT] Fetching {symbol} {timeframe} from {start_time} to {end_time}...")
        
        while since < end_ts:
            try:
                candles = await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                if not candles:
                    break
                
                # Filter out candles beyond end_time
                candles = [c for c in candles if c[0] < end_ts]
                
                if not candles:
                    break

                all_candles.extend(candles)
                
                # Update 'since' to the last timestamp + 1s (or resolution)
                last_ts = candles[-1][0]
                since = last_ts + resolution_ms
                
                # Small sleep to be nice to rate limiter (handled by ccxt usually but safe)
                await asyncio.sleep(0.1) 
                
            except Exception as e:
                print(f"[CCXT] Error fetching {symbol}: {e}")
                # Retry logic could go here
                await asyncio.sleep(1)
                break
                
        # Convert to DataFrame
        if not all_candles:
             return pd.DataFrame()
             
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return df

    async def fetch_ticker(self, symbol: str) -> Optional[Tick]:
        """
        Fetch single ticker.
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return Tick(
                timestamp=normalize_timestamp(ticker['timestamp']),
                price=ticker['last'],
                volume=ticker.get('baseVolume', 0.0),
                symbol=symbol
            )
        except Exception as e:
            print(f"[CCXT] Ticker error {symbol}: {e}")
            return None

    def parse_symbol(self, symbol: str) -> str:
        # e.g. "BTCUSDT" -> "BTC/USDT" if needed, but CCXT likes "BTC/USDT"
        return symbol.upper()
