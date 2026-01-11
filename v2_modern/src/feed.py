import time
import ccxt
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

class MarketDataFeed:
    def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        """Returns current ticker data for list of symbols."""
        raise NotImplementedError

    def sleep(self, seconds: float):
        raise NotImplementedError

    def now(self) -> float:
        raise NotImplementedError

    def is_finished(self) -> bool:
        return False

# --- Live Feed ---
class LiveFeed(MarketDataFeed):
    def __init__(self, exchange_id='kraken'):
        self.exchange = None
        try:
            print(f"Connecting to {exchange_id}...")
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({
                'timeout': 10000,
                'enableRateLimit': True
            })
            print(f"Connected to {exchange_id}.")
        except Exception as e:
            print(f"Warning: Failed to init {exchange_id}: {e}")

    def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        if not self.exchange: return {}
        try:
            return self.exchange.fetch_tickers(symbols)
        except Exception as e:
            print(f"LiveFeed fetch error: {e}")
            return {}

    def sleep(self, seconds: float):
        time.sleep(seconds)

    def now(self) -> float:
        return time.time()

# --- Historical Feed ---
class HistoricalFeed(MarketDataFeed):
    def __init__(self, historical_data: Dict[str, Dict[int, Dict]], start_ms: int, end_ms: int, speed: str = "max"):
        self.data = historical_data
        self.current_time_ms = start_ms
        self.end_time_ms = end_ms
        self.speed = speed
        self.current_prices = {sym: 0.0 for sym in self.data.keys()}
        
    def _interpolate_price(self, symbol: str, time_ms: int) -> float:
        candle_start_ms = (time_ms // 60000) * 60000
        candle = self.data.get(symbol, {}).get(candle_start_ms)
        
        if not candle:
            return self.current_prices.get(symbol, 0.0)

        o, h, l, c = candle['o'], candle['h'], candle['l'], candle['c']
        offset = time_ms - candle_start_ms
        
        # Simple Triangle Interpolation
        if offset < 20000:   return o + (h - o) * (offset / 20000)
        elif offset < 40000: return h + (l - h) * ((offset - 20000) / 20000)
        else:                return l + (c - l) * ((offset - 40000) / 20000)

    def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        tickers = {}
        for sym in symbols:
            price = self._interpolate_price(sym, self.current_time_ms)
            self.current_prices[sym] = price
            tickers[sym] = {
                'symbol': sym,
                'timestamp': self.current_time_ms,
                'last': price,
                'close': price # Added for compatibility
            }
        return tickers

    def sleep(self, seconds: float):
        self.current_time_ms += int(seconds * 1000)
        if self.speed == "realtime": time.sleep(seconds)
        elif self.speed == "10x": time.sleep(seconds / 10)

    def now(self) -> float:
        return self.current_time_ms / 1000.0

    def is_finished(self) -> bool:
        return self.current_time_ms >= self.end_time_ms

# --- Data Loader ---
class DataLoader:
    @staticmethod
    def load_csv(file_path: str) -> Optional[Dict[str, Dict[int, Dict]]]:
        print(f"Loading data from {file_path}...")
        try:
            # Check header
            with open(file_path, 'r') as f:
                first_line = f.readline()
                has_header = "Symbol" in first_line or "Timestamp" in first_line

            if has_header:
                df = pd.read_csv(file_path, low_memory=False)
            else:
                headers = [
                    "Timestamp_IST", "Symbol", "State", "Regime", 
                    "Velocity", "Entry_Vel", "Decay", "Heat", "EQS", 
                    "Action", "Message", "Price", "MFE", "Exit_Reason",
                    "Open", "High", "Low", "Close", "Volume"
                ]
                df = pd.read_csv(file_path, names=headers, low_memory=False)

            data = {}
            for _, row in df.iterrows():
                symbol = row['Symbol']
                # Try parsing timestamp
                ts = DataLoader._parse_timestamp(row)
                if ts == 0: continue

                if symbol not in data: data[symbol] = {}
                data[symbol][ts] = {
                    'o': float(row.get('Open', 0)),
                    'h': float(row.get('High', 0)),
                    'l': float(row.get('Low', 0)),
                    'c': float(row.get('Close', 0)),
                    'v': float(row.get('Volume', 0))
                }
            return data
        except Exception as e:
            print(f"Failed to load CSV: {e}")
            return None

    @staticmethod
    def _parse_timestamp(row) -> int:
        val = row.get('Timestamp_IST', row.get('Timestamp'))
        try:
            return int(float(val) * 1000)
        except:
            try:
                dt = datetime.strptime(str(val), "%Y-%m-%d %H:%M:%S")
                # Assume IST fetch
                return int(dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30))).timestamp() * 1000)
            except:
                return 0

    @staticmethod
    def fetch_historical(exchange_id, symbols, start_ms, end_ms):
         # Wraps CCXT fetch_ohlcv loop
        print(f"Fetching {len(symbols)} symbols from {exchange_id}...")
        exchange = getattr(ccxt, exchange_id)()
        data = {}
        for sym in symbols:
            print(f"  Fetching {sym}...")
            candles = []
            since = start_ms
            while since < end_ms:
                try:
                    batch = exchange.fetch_ohlcv(sym, '1m', since=since, limit=1000)
                    if not batch: break
                    candles.extend(batch)
                    since = batch[-1][0] + 60000
                    time.sleep(exchange.rateLimit / 1000)
                except Exception as e:
                    print(f"    Error: {e}")
                    break
            
            # Format to dict
            data[sym] = {}
            for c in candles:
                if c[0] >= start_ms and c[0] <= end_ms:
                    data[sym][c[0]] = {'o': c[1], 'h': c[2], 'l': c[3], 'c': c[4], 'v': c[5]}
        return data
