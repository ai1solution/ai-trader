"""
Technical Indicators for Strategies.
"""
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple

def calculate_velocity(prices: List[float], period: int = 12) -> Optional[float]:
    """
    Calculate price velocity (ROC normalized by period).
    Velocity = (Price[0] - Price[-period]) / Price[-period]
    """
    if len(prices) < period + 1:
        return None
    
    current = prices[-1]
    past = prices[-(period + 1)]
    
    if past == 0: return 0.0
    
    return (current - past) / past

def calculate_velocity_acceleration(velocities: List[float], period: int = 5) -> bool:
    """
    Check if velocity is accelerating (median of recent > median of older).
    """
    if len(velocities) < period * 2:
        return True # Not enough data, assume neutral/continuing
        
    recent = velocities[-period:]
    older = velocities[-2*period:-period]
    
    return np.median(recent) > np.median(older)

def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate RSI from a list of prices.
    """
    if len(prices) < period + 1:
        return None
        
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    
    if down == 0: return 100.0
    rs = up / down
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_bollinger_bands(prices: List[float], period: int = 20, num_std: float = 2.0) -> Optional[Tuple[float, float, float]]:
    """
    Calculate Bollinger Bands (Upper, Middle, Lower).
    """
    if len(prices) < period:
        return None
        
    window = prices[-period:]
    sma = float(np.mean(window))
    std = float(np.std(window))
    
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    
    return upper, sma, lower

def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average (EMA).
    """
    if len(prices) < period:
        return None
        
    if len(prices) > 1000:
        return pd.Series(prices).ewm(span=period, adjust=False).mean().iloc[-1]
        
    return pd.Series(prices).ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Average True Range (ATR).
    """
    if len(closes) < period + 1:
        return None
        
    df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    
    atr = df['tr'].rolling(window=period).mean().iloc[-1]
    return float(atr)
