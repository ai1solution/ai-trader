"""
Market Regime Classification.
Detects Trending vs Ranging regimes.
"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ..data.ccxt_provider import CCXTProvider
from ..strategies.indicators import calculate_ema, calculate_atr

class MarketRegime:
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    UNCERTAIN = "UNCERTAIN"

class RegimeClassifier:
    def __init__(self):
        self.provider = CCXTProvider()
        # Symbol -> Date -> Regime
        self.regime_cache: Dict[str, Dict[str, str]] = {} 
        # Symbol -> DataFrame (Daily)
        self.daily_data: Dict[str, pd.DataFrame] = {}
        
        self.cache_duration = timedelta(minutes=15) 
        
        # Hysteresis State
        self.consecutive_trend_signals: Dict[str, int] = {}
        self.consecutive_range_signals: Dict[str, int] = {}
        self.current_regime: Dict[str, str] = {} 
        
        self.hysteresis_threshold = 2

    def preload_data(self, symbol: str, df: pd.DataFrame):
        """
        Pre-load daily data for the symbol to enable offline regime checks.
        """
        if df is None or df.empty:
            return
            
        # Ensure UTC and sorted
        df = df.sort_values('timestamp').copy()
        
        # Pre-calculate indicators for the whole dataframe at once!
        # This is O(N) once, vs O(N) every tick.
        # Calculate ADX, EMA, etc.
        df = self._calculate_indicators(df)
        self.daily_data[symbol] = df
        
        # Pre-compute regime for every day? 
        # Or compute on demand (O(1) lookup in DF)?
        # Let's compute on demand but using the pre-calculated columns.
        print(f"[Regime] Preloaded {len(df)} days for {symbol}")

    async def get_regime(self, symbol: str, current_time: datetime) -> str:
        """
        Determine regime for symbol synchronously (logically) using pre-fetched data.
        Returns MarketRegime constant.
        """
        # 1. Lookup in Cache (if we cached exact timestamp logic, but dates define regime)
        date_key = current_time.strftime("%Y-%m-%d")
        
        if symbol not in self.regime_cache:
            self.regime_cache[symbol] = {}
            
        if date_key in self.regime_cache[symbol]:
            return self.regime_cache[symbol][date_key]
            
        # 2. If not in cache, compute from Daily Data
        if symbol not in self.daily_data:
            # If no data preloaded, we cannot determine regime without network.
            return MarketRegime.UNCERTAIN

        df = self.daily_data[symbol]
        
        # Find the row for 'yesterday' or 'today' depending on logic.
        # Ideally, Regime is based on "Closed Daily Candle" of Yesterday.
        # current_time is e.g. 2024-01-01 10:00:00.
        # We need indicators based on data available UP TO this point.
        # Usually that means the daily candle of 2023-12-31.
        
        # Filter for rows strictly before current_time
        # Since we pre-calculated indicators, we just pick the last row.
        
        # Fast search:
        # Assuming daily candles are at 00:00:00.
        # If current_time is 2024-01-01 10:00:00, the last closed candle is 2024-01-01 00:00:00? 
        # No, 00:00:00 usually effectively means the day *started*.
        # Only if we treat it as previous day close. 
        # Standard: If timestamp is "Start of Day", then 2024-01-01 00:00:00 represents the candle for Jan 1st.
        # It closes at Jan 2nd 00:00:00.
        # So at 10:00:00 Jan 1st, the last *closed* candle is Dec 31st.
        
        # Mask: timestamp < current_time - 1 day? Or just < current_time and assume open candle is not in DF?
        # Safe bet: Get last row where timestamp < current_time.
        # But wait, if we are mid-day Jan 1st, we shouldn't peek at Jan 1st close.
        # Our pre-loader loads known historical data.
        
        past_df = df[df['timestamp'] < current_time]
        if past_df.empty:
             return MarketRegime.UNCERTAIN
             
        row = past_df.iloc[-1]
        
        # Check if this row is too old (stale)
        # e.g. > 2 days old
        row_ts = row['timestamp']
        if (current_time - row_ts).days > 3:
            return MarketRegime.UNCERTAIN
            
        # 3. Apply Logic
        regime = self._classify_row(row)
        
        # 4. Hysteresis (Simplified: For now, just instant, or use memory)
        # To strictly implement hysteresis, we need sequential processing.
        # But here we are jumping to a date. 
        # If we stick to "Regime is property of Day D", we can ignore hysteresis or compute it sequentially during preload.
        # Let's compute sequentially during preload!
        
        # Actually, let's just apply the same hysteresis logic but persist it in the 'regime_cache' 
        # as we progress. But 'get_regime' might be called out of order? 
        # No, backtest is sequential.
        
        # Apply Hysteresis
        final_regime = self._apply_hysteresis(symbol, regime)
        
        # Cache it
        self.regime_cache[symbol][date_key] = final_regime
        return final_regime

    def _calculate_indicators(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        df = df.copy()
        
        # ADX
        df['up'] = df['high'] - df['high'].shift(1)
        df['down'] = df['low'].shift(1) - df['low']
        df['pdm'] = np.where((df['up'] > df['down']) & (df['up'] > 0), df['up'], 0)
        df['ndm'] = np.where((df['down'] > df['up']) & (df['down'] > 0), df['down'], 0)
        
        # Vectorized ATR
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = abs(high - low)
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_series = tr.rolling(window=period).mean()
        
        pdm_s = df['pdm'].rolling(window=period).mean()
        ndm_s = df['ndm'].rolling(window=period).mean()
        
        pdi = 100 * (pdm_s / atr_series)
        ndi = 100 * (ndm_s / atr_series)
        dx = 100 * abs(pdi - ndi) / (pdi + ndi)
        df['adx'] = dx.rolling(window=period).mean()
        
        # EMA
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        return df

    def _classify_row(self, row) -> str:
        if pd.isna(row['adx']):
            return MarketRegime.UNCERTAIN
            
        adx = row['adx']
        ema_20 = row['ema_20']
        ema_50 = row['ema_50']
        
        if adx > 25:
            return MarketRegime.TRENDING
        elif adx < 20:
             return MarketRegime.RANGING
        else:
            diff = abs(ema_20 - ema_50) / ema_50
            if diff < 0.02:
                return MarketRegime.RANGING
            else:
                return MarketRegime.TRENDING

    def _apply_hysteresis(self, symbol: str, signal_regime: str) -> str:
        # Initialize
        if symbol not in self.current_regime:
            self.current_regime[symbol] = MarketRegime.RANGING
            self.consecutive_trend_signals[symbol] = 0
            self.consecutive_range_signals[symbol] = 0
            
        current = self.current_regime[symbol]
        
        if signal_regime == MarketRegime.TRENDING:
            self.consecutive_trend_signals[symbol] += 1
            self.consecutive_range_signals[symbol] = 0
            if self.consecutive_trend_signals[symbol] >= self.hysteresis_threshold:
                current = MarketRegime.TRENDING
        elif signal_regime == MarketRegime.RANGING:
            self.consecutive_range_signals[symbol] += 1
            self.consecutive_trend_signals[symbol] = 0
            if self.consecutive_range_signals[symbol] >= self.hysteresis_threshold:
                current = MarketRegime.RANGING
                
        self.current_regime[symbol] = current
        return current

    async def cleanup(self):
        await self.provider.cleanup()
