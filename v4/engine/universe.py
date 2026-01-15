"""
Universe Selection Logic.
Filters symbols based on price, volume, and volatility.
"""
from typing import List, Dict
from datetime import datetime
import pandas as pd
from ..data.ccxt_provider import CCXTProvider
from ..strategies.indicators import calculate_atr

class UniverseSelector:
    def __init__(self, config: Dict):
        self.config = config
        self.provider = CCXTProvider()
        
        # Criteria
        # Criteria
        # Config passed is the 'universe' section dict
        self.min_price = config.get('min_price', 0.01)
        self.min_volume = config.get('min_volume_24h', 1000000.0)
        self.min_atr_pct = config.get('min_atr_pct', 0.02) # 2% daily range
        self.excluded_tags = ['meme', 'micro'] # not really tags in ccxt, but we filter by explicit list
        
        # Explicit exclusions (Micro-memes as requested)
        self.blacklist = []
        #     "PEPE/USDT", "BONK/USDT", "WIF/USDT", "FLOKI/USDT", 
        #     "MEME/USDT", "BOME/USDT", "SHIB/USDT", "DOGE/USDT"
        # ]

    async def select_symbols(self, candidates: List[str], refernece_time: datetime = None) -> List[str]:
        """
        Filter the candidate list.
        """
        print(f"[Universe] Filtering {len(candidates)} candidates...")
        selected = []
        
        # Pre-fetch stats (using CCXTProvider)
        # For backtest, we need data 'before' reference_time.
        # For simplicity in this research harness, we might check the 'previous day' candle.
        
        for symbol in candidates:
            # 1. Explicit Blacklist
            if symbol in self.blacklist:
                print(f"[Universe] REJECT {symbol}: Blacklisted (Meme/Micro)")
                continue
                
            try:
                # Fetch recent daily data (Need at least 14 days for ATR)
                limit = 20
                if refernece_time:
                    # Logic to fetch data ending before reference_time is needed
                    # Provider fetch_ohlcv supports 'since', but need 'until'.
                    # For now, let's just fetch recent and assume backtest start is recent enough 
                    # OR properly slice. The provider in v4 is simple.
                    # We will fetch last 20 days relative to *now* for live, or *start_date* for backtest.
                    # Assuming provider handles this or we just fetch last 20 days from start.
                    end_dt = refernece_time
                    start_dt = end_dt - pd.Timedelta(days=30)
                    df = await self.provider.fetch_ohlcv(symbol, '1d', start_dt, end_dt)
                if df is None or df.empty or len(df) < 14:
                    print(f"[Universe] REJECT {symbol}: Insufficient Data")
                    continue
                    
                last_row = df.iloc[-1]
                last_price = last_row['close']
                
                # 2. Blacklist (Meme/Micro-cap filter) - DISABLED FOR TESTING
                # if any(b in symbol for b in ["PEPE", "BONK", "FLOKI", "WIF", "MEME", "BOME", "SHIB", "DOGE"]):
                #    print(f"[Universe] REJECT {symbol}: Blacklisted (Meme/Micro)")
                #    continue

                # 3. Min Price
                if last_price < self.min_price:
                     print(f"[Universe] REJECT {symbol}: Price {last_price} < {self.min_price}")
                     # continue # Relaxed for meme testing
                    
                # 3. Min Volume (24h)
                # Approximation using last daily volume * last price (Quote Volume)
                vol_24h = last_row['volume'] * last_row['close']
                if vol_24h < self.min_volume:
                    print(f"[Universe] REJECT {symbol}: Volume {vol_24h:.0f} < {self.min_volume}")
                    continue
                    
                # 4. Volatility (ATR %)
                atr = calculate_atr(df['high'].tolist(), df['low'].tolist(), df['close'].tolist(), 14)
                if atr is None:
                    continue
                    
                atr_pct = atr / last_row['close']
                if atr_pct < self.min_atr_pct:
                    print(f"[Universe] REJECT {symbol}: ATR {atr_pct:.2%} < {self.min_atr_pct:.2%}")
                    continue
                    
                selected.append(symbol)
                
            except Exception as e:
                print(f"[Universe] Error checking {symbol}: {e}")
                
        print(f"[Universe] Selected {len(selected)}/{len(candidates)} symbols.")
        return selected

    async def cleanup(self):
        await self.provider.cleanup()
