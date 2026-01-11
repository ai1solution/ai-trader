from typing import List
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
import queue
import ccxt

# Mock Tick to avoid imports
class Tick:
    def __init__(self, timestamp, price, volume):
        self.timestamp = timestamp
        self.price = price
        self.volume = volume
    def __repr__(self):
        return f"Tick({self.timestamp}, {self.price})"

class CentralMarketData:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        # Convert to exchange format (e.g. SUIUSDT -> SUI/USDT)
        self.api_symbols = [s.replace("USDT", "/USDT") if "/" not in s else s for s in symbols]
        self.symbol_map = {api: orig for api, orig in zip(self.api_symbols, symbols)}
        
        self.queues = defaultdict(list)
        self.running = True
        self.exchange = ccxt.binance({'enableRateLimit': True})
        
    def create_feed(self, symbol: str):
        q = queue.Queue()
        self.queues[symbol].append(q)
        return q
        
    def run_once(self):
        try:
            print(f"Fetching for: {self.api_symbols}")
            tickers = self.exchange.fetch_tickers(self.api_symbols)
            print(f"Got {len(tickers)} tickers")
            
            current_time = datetime.now(timezone.utc)
            
            for api_symbol, ticker_data in tickers.items():
                internal_symbol = self.symbol_map.get(api_symbol)
                # Debug mismatch
                if not internal_symbol:
                    print(f"WARNING: Unmapped symbol {api_symbol}")
                    if api_symbol in self.queues:
                        internal_symbol = api_symbol
                    else:
                        continue
                
                price = ticker_data['last']
                print(f"  {internal_symbol}: {price}")
                
                tick = Tick(current_time, price, 0)
                
                for q in self.queues[internal_symbol]:
                    q.put(tick)
                    
        except Exception as e:
            print(f"ERROR: {e}")

VOLATILE_COINS_15 = [
    "SUIUSDT", "SNXUSDT", "XRPUSDT", "INJUSDT", "AAVEUSDT",
    "BONKUSDT", "WIFUSDT", "PEPEUSDT", "FLOKIUSDT", "MEMEUSDT",
    "SHIBUSDT", "ORDIUSDT", "FILUSDT", "UNIUSDT", "TIAUSDT"
]

if __name__ == "__main__":
    hub = CentralMarketData(VOLATILE_COINS_15)
    # create feed for one
    q = hub.create_feed("SUIUSDT")
    hub.run_once()
    
    try:
        t = q.get(block=False)
        print(f"Queue got: {t}")
    except:
        print("Queue Empty!")
